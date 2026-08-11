"""Run imported-baseline and semantic-score pilot acceptance against Compose."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from numbers import Real
from pathlib import Path
from uuid import uuid4

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from agentlens import instrument
from agentlens_worker.baseline import manifest_for_records
from opentelemetry import trace

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "infra/compose/docker-compose.yaml"


class PackageServer:
    def __init__(self, directory: Path) -> None:
        handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
        self.server = ThreadingHTTPServer(("0.0.0.0", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    def __enter__(self) -> PackageServer:
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _request(url: str, *, method: str = "GET", body: object | None = None) -> object:
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        method=method,
        data=payload,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def _wait_for_import(api_url: str, import_id: str, deadline: float) -> dict[str, object]:
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        result = _request(f"{api_url.rstrip('/')}/v1/baseline-imports/{import_id}")
        if isinstance(result, dict) and result.get("status") in {"validated", "failed"}:
            return result
        time.sleep(1)
    raise TimeoutError(f"baseline import {import_id} did not finish within {deadline}s")


def _wait_for_semantic_score(
    api_url: str, trace_id: str, deadline: float
) -> tuple[dict[str, object], float]:
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            result = _request(f"{api_url.rstrip('/')}/v1/executions/{trace_id}/scores")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                time.sleep(1)
                continue
            raise
        if isinstance(result, list):
            complete = [
                item
                for item in result
                if isinstance(item, dict) and item.get("status") == "complete"
            ]
            if complete:
                return complete[-1], time.monotonic()
        time.sleep(1)
    raise TimeoutError(f"semantic score for {trace_id} did not complete within {deadline}s")


def _create_package(
    directory: Path,
    *,
    tenant: str,
    environment: str,
    agent_name: str,
    agent_version: str,
    dimensions: int,
    records: int,
) -> tuple[Path, str, str]:
    package_dir = directory / "baseline"
    package_dir.mkdir()
    records_path = package_dir / "records.parquet"
    rng = np.random.default_rng(20260811)
    recipes = (
        ("lookup", ["search", "answer"], 0.0),
        ("lookup", ["lookup", "answer"], 0.001),
        ("update", ["fetch", "write"], -0.001),
        ("support", ["retrieve", "answer"], 0.002),
    )
    rows = []
    for index in range(records):
        intent, tool_path, offset = recipes[index % len(recipes)]
        input_embedding = rng.normal(0, 0.01, dimensions)
        output_embedding = rng.normal(0, 0.01, dimensions)
        input_embedding[0] += offset
        output_embedding[0] += offset
        rows.append(
            {
                "success": True,
                "intent": intent,
                "input_embedding": input_embedding.astype(float).tolist(),
                "output_embedding": output_embedding.astype(float).tolist(),
                "input_entropy": 0.1 + (index % 10) / 100,
                "tool_path": tool_path,
            }
        )
    pq.write_table(pa.Table.from_pylist(rows), records_path)
    baseline_id = uuid4()
    manifest = manifest_for_records(
        baseline_id=baseline_id,
        tenant_id=tenant,
        environment=environment,
        agent_name=agent_name,
        agent_version=agent_version,
        model="text-embedding-3-small",
        dimensions=dimensions,
        records_path=records_path,
        record_count=records,
        created_at=time_to_datetime(),
    )
    (package_dir / "manifest.json").write_text(manifest.model_dump_json())
    archive = directory / "baseline.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.write(package_dir / "manifest.json", arcname="manifest.json")
        zipped.write(records_path, arcname="records.parquet")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    return archive, checksum, str(baseline_id)


def time_to_datetime() -> datetime:
    return datetime.now(UTC)


def _emit_trace(endpoint: str, baseline_ref: str) -> tuple[str, float]:
    provider = instrument(
        framework="generic",
        agent_name="semantic-acceptance-agent",
        agent_version="1.0.0",
        environment="development",
        baseline_ref=baseline_ref,
        otlp_endpoint=endpoint,
        insecure=True,
    )
    tracer = trace.get_tracer("agentlens.semantic-acceptance")
    started = time.monotonic()
    with tracer.start_as_current_span("agent.run") as root:
        root.set_attribute("input.value", "semantic acceptance input")
        root.set_attribute("output.value", "semantic acceptance output")
        root.set_attribute("gen_ai.usage.input_tokens", 10)
        root.set_attribute("gen_ai.usage.output_tokens", 12)
        with tracer.start_as_current_span("lookup") as child:
            child.set_attribute("tool.name", "lookup")
        trace_id = f"{root.get_span_context().trace_id:032x}"
    provider.force_flush(timeout_millis=10_000)
    provider.shutdown()
    return trace_id, started


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:18000")
    parser.add_argument("--edge-endpoint", default="http://localhost:4317")
    parser.add_argument("--deadline-seconds", type=float, default=60)
    parser.add_argument("--records", type=int, default=500)
    parser.add_argument("--dimensions", type=int, default=1536)
    parser.add_argument("--traces", type=int, default=5)
    args = parser.parse_args()
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        raise SystemExit(
            "OPENAI_API_KEY is required: provide an approved embedding "
            "credential for semantic acceptance"
        )
    if args.records < 500 or args.dimensions < 8 or args.traces < 2:
        parser.error("records must be at least 500, dimensions at least 8, and traces at least 2")

    compose_env = os.environ.copy()
    compose_env["OPENAI_API_KEY"] = openai_api_key
    compose_env["SEMANTIC_NORMAL_SAMPLE_RATE"] = "1"
    env_file = ROOT / (".env" if (ROOT / ".env").is_file() else ".env.example")
    subprocess_command = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(COMPOSE_FILE),
        "up",
        "-d",
        "--build",
        "worker-baseline-import",
        "worker-normalize",
        "worker-assemble",
        "worker-score",
        "otel-platform",
        "otel-edge",
        "api",
    ]
    subprocess.run(subprocess_command, cwd=ROOT, check=True, env=compose_env)
    with tempfile.TemporaryDirectory(prefix="agentlens-semantic-acceptance-") as tmp:
        archive, checksum, expected_baseline_id = _create_package(
            Path(tmp),
            tenant="local",
            environment="development",
            agent_name="semantic-acceptance-agent",
            agent_version="1.0.0",
            dimensions=args.dimensions,
            records=args.records,
        )
        with PackageServer(Path(tmp)) as server:
            object_uri = f"http://host.docker.internal:{server.port}/{archive.name}"
            created = _request(
                f"{args.api_url.rstrip('/')}/v1/baseline-imports",
                method="POST",
                body={"object_uri": object_uri, "checksum": checksum},
            )
            if not isinstance(created, dict):
                raise RuntimeError("baseline import API returned an invalid response")
            import_id = str(created["import_id"])
            imported = _wait_for_import(args.api_url, import_id, args.deadline_seconds)
            if imported.get("status") != "validated":
                raise RuntimeError(f"baseline import failed: {imported}")
            baseline_id = str(imported.get("baseline_id"))
            if baseline_id != expected_baseline_id:
                raise RuntimeError("validated baseline identity does not match manifest")
            activation = _request(
                f"{args.api_url.rstrip('/')}/v1/baselines/{baseline_id}/activate", method="POST"
            )
            if not isinstance(activation, dict) or activation.get("status") != "active":
                raise RuntimeError(f"baseline activation failed: {activation}")
            emissions = [_emit_trace(args.edge_endpoint, baseline_id) for _ in range(args.traces)]
            results: list[tuple[str, dict[str, object], float]] = []
            for trace_id, emitted_at in emissions:
                score, completed_at = _wait_for_semantic_score(
                    args.api_url, trace_id, args.deadline_seconds
                )
                if score.get("baseline_id") != baseline_id or score.get("status") != "complete":
                    raise RuntimeError(f"semantic score did not use the active baseline: {score}")
                if score.get("mahalanobis_distance") is None:
                    raise RuntimeError("semantic score is missing Mahalanobis distance")
                results.append((trace_id, score, completed_at - emitted_at))
            distance_values = [score.get("mahalanobis_distance") for _, score, _ in results]
            if not all(isinstance(value, Real) for value in distance_values):
                raise RuntimeError("semantic score distance is not numeric")
            distances = [float(value) for value in distance_values if isinstance(value, Real)]
            if max(distances) - min(distances) > 1e-6:
                raise RuntimeError(f"repeated semantic score is not deterministic: {distances}")
            freshness = [latency for _, _, latency in results]
            freshness_p95 = float(np.percentile(freshness, 95))
            if freshness_p95 >= 60:
                raise RuntimeError(
                    f"semantic score freshness p95 exceeded 60 seconds: {freshness_p95}"
                )
            findings = _request(f"{args.api_url.rstrip('/')}/v1/findings?limit=200")
            finding_trace_ids = (
                {
                    item.get("trace_id")
                    for item in findings
                    if isinstance(item, dict) and item.get("trace_id")
                }
                if isinstance(findings, list)
                else set()
            )
            expected_trace_ids = {trace_id for trace_id, _, _ in results}
            missing_findings = expected_trace_ids - finding_trace_ids
            if missing_findings:
                raise RuntimeError(
                    f"semantic acceptance did not create findings: {missing_findings}"
                )
            trace_id, score, _ = results[0]
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "baseline_id": baseline_id,
                        "trace_id": trace_id,
                        "score_status": score["status"],
                        "mahalanobis_distance": score["mahalanobis_distance"],
                        "finding_count": len(expected_trace_ids),
                        "freshness_p95_seconds": round(freshness_p95, 3),
                        "freshness_target_seconds": 60,
                        "repeated_trace_count": len(results),
                        "deterministic_distance_delta": round(max(distances) - min(distances), 12),
                    },
                    sort_keys=True,
                )
            )


if __name__ == "__main__":
    main()
