"""Build, import, and activate a baseline from clear demo prompts.

Embeddings come from the same OpenAI-compatible endpoint the score worker uses.
Vectors are cached under examples/drift-demo/.cache so a second run does not
re-embed identical prompts.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
import threading
import time
import zipfile
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from agentlens_worker.baseline import manifest_for_records
from agentlens_worker.features import shannon_entropy

from .agent import SupportAgent
from .client import request_json, wait_until_ready
from .identity import AGENT_NAME, AGENT_VERSION, ENVIRONMENT, TENANT_ID
from .prompts import CLEAR, baseline_prompt

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
MIN_RECORDS = 500


class PackageServer:
    def __init__(self, directory: Path) -> None:
        handler = partial(_QuietHandler, directory=str(directory))
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


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def embedding_settings() -> tuple[str, str, str | None]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is required to build the demo baseline. "
            "Traffic can still be sent without it; only volatility and tool-failure "
            "findings will be produced."
        )
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()
    if api_key.startswith("sk-or-v1-"):
        base_url = base_url or "https://openrouter.ai/api/v1"
        model = model or "openai/text-embedding-3-small"
    return api_key, model or "text-embedding-3-small", base_url


def cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def baseline_id_path() -> Path:
    return cache_dir() / "baseline.json"


def load_baseline_id() -> str | None:
    path = baseline_id_path()
    if not path.is_file():
        return None
    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and payload.get("baseline_id"):
        return str(payload["baseline_id"])
    return None


def build_clear_rows(count: int, seed: int) -> list[dict[str, object]]:
    if count < MIN_RECORDS:
        raise ValueError(f"baseline needs at least {MIN_RECORDS} records")
    rng = random.Random(seed)
    agent = SupportAgent()
    rows: list[dict[str, object]] = []
    for _ in range(count):
        intent, prompt = baseline_prompt(rng)
        plan = agent.plan(prompt, CLEAR, intent)
        entropy = shannon_entropy(prompt)
        if entropy is None:
            raise RuntimeError("clear baseline prompt produced no entropy")
        rows.append(
            {
                "success": True,
                "intent": intent,
                "prompt": prompt,
                "output": plan.output,
                "input_entropy": entropy,
                "tool_path": plan.tool_path,
            }
        )
    return rows


def attach_embeddings(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], str, int]:
    api_key, model, base_url = embedding_settings()
    texts: list[str] = []
    for row in rows:
        texts.append(str(row["prompt"]))
        texts.append(str(row["output"]))
    vectors = _embed_cached(texts, api_key=api_key, model=model, base_url=base_url)
    dimensions = len(next(iter(vectors.values())))
    embedded: list[dict[str, object]] = []
    for row in rows:
        embedded.append(
            {
                "success": True,
                "intent": row["intent"],
                "input_embedding": vectors[str(row["prompt"])],
                "output_embedding": vectors[str(row["output"])],
                "input_entropy": row["input_entropy"],
                "tool_path": row["tool_path"],
            }
        )
    return embedded, model, dimensions


def write_package(
    directory: Path,
    rows: list[dict[str, object]],
    *,
    model: str,
    dimensions: int,
) -> tuple[Path, str, str]:
    package_dir = directory / "baseline"
    package_dir.mkdir()
    records_path = package_dir / "records.parquet"
    pq.write_table(pa.Table.from_pylist(rows), records_path)
    baseline_id = uuid4()
    manifest = manifest_for_records(
        baseline_id=baseline_id,
        tenant_id=TENANT_ID,
        environment=ENVIRONMENT,
        agent_name=AGENT_NAME,
        agent_version=AGENT_VERSION,
        model=model,
        dimensions=dimensions,
        records_path=records_path,
        record_count=len(rows),
        created_at=datetime.now(UTC),
    )
    (package_dir / "manifest.json").write_text(manifest.model_dump_json())
    archive = directory / "baseline.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.write(package_dir / "manifest.json", arcname="manifest.json")
        zipped.write(records_path, arcname="records.parquet")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    return archive, checksum, str(baseline_id)


def import_and_activate(
    *,
    api_url: str,
    archive: Path,
    checksum: str,
    deadline: float,
) -> str:
    wait_until_ready(api_url, deadline)
    with PackageServer(archive.parent) as server:
        object_uri = f"http://host.docker.internal:{server.port}/{archive.name}"
        created = request_json(
            f"{api_url.rstrip('/')}/v1/baseline-imports",
            method="POST",
            body={"object_uri": object_uri, "checksum": checksum},
        )
        if not isinstance(created, dict) or "import_id" not in created:
            raise RuntimeError(f"baseline import API returned an invalid response: {created}")
        imported = _wait_for_import(api_url, str(created["import_id"]), deadline)
        if imported.get("status") != "validated":
            raise RuntimeError(f"baseline import failed: {imported}")
        baseline_id = str(imported["baseline_id"])
        activation = request_json(
            f"{api_url.rstrip('/')}/v1/baselines/{baseline_id}/activate",
            method="POST",
        )
        if not isinstance(activation, dict) or activation.get("status") != "active":
            raise RuntimeError(f"baseline activation failed: {activation}")
    return baseline_id


def bootstrap(*, api_url: str, records: int, seed: int, deadline: float) -> str:
    print(
        f"Building {records} clear demo executions for {AGENT_NAME} "
        f"(environment={ENVIRONMENT})"
    )
    rows = build_clear_rows(records, seed)
    embedded, model, dimensions = attach_embeddings(rows)
    print(f"Embedded with {model} ({dimensions} dimensions)")
    with tempfile.TemporaryDirectory(prefix="agentlens-drift-demo-") as tmp:
        archive, checksum, _ = write_package(
            Path(tmp), embedded, model=model, dimensions=dimensions
        )
        baseline_id = import_and_activate(
            api_url=api_url,
            archive=archive,
            checksum=checksum,
            deadline=deadline,
        )
    payload = {
        "baseline_id": baseline_id,
        "agent_name": AGENT_NAME,
        "agent_version": AGENT_VERSION,
        "environment": ENVIRONMENT,
        "embedding_model": model,
    }
    baseline_id_path().write_text(json.dumps(payload, indent=2))
    print(f"Activated demo baseline {baseline_id}")
    return baseline_id


def _embed_cached(
    texts: list[str],
    *,
    api_key: str,
    model: str,
    base_url: str | None,
) -> dict[str, list[float]]:
    from openai import OpenAI

    cache_path = cache_dir() / f"embeddings-{model.replace('/', '_')}.json"
    cache: dict[str, list[float]] = {}
    if cache_path.is_file():
        loaded = json.loads(cache_path.read_text())
        if isinstance(loaded, dict):
            cache = {str(key): [float(item) for item in value] for key, value in loaded.items()}
    missing = [text for text in dict.fromkeys(texts) if text not in cache]
    if missing:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=3)
        print(f"Embedding {len(missing)} new demo strings")
        for start in range(0, len(missing), 64):
            batch = missing[start : start + 64]
            response = client.embeddings.create(model=model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            for text, item in zip(batch, ordered, strict=True):
                cache[text] = [float(value) for value in item.embedding]
        cache_path.write_text(json.dumps(cache))
    return {text: cache[text] for text in dict.fromkeys(texts)}


def _wait_for_import(api_url: str, import_id: str, deadline: float) -> dict[str, object]:
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        result = request_json(f"{api_url.rstrip('/')}/v1/baseline-imports/{import_id}")
        if isinstance(result, dict) and result.get("status") in {"validated", "failed"}:
            return result
        time.sleep(1)
    raise TimeoutError(f"baseline import {import_id} did not finish within {deadline:.0f}s")
