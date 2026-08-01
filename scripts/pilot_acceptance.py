"""Exercise local pilot ingestion, freshness, privacy, and API concurrency gates."""

from __future__ import annotations

import argparse
import base64
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from uuid import uuid4

from agentlens import instrument
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


@dataclass(frozen=True, slots=True)
class EmittedTrace:
    trace_id: str
    marker: str
    emitted_at: float


def _json(url: str, *, timeout: float = 10) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _clickhouse_count(endpoint: str, query: str, *, username: str, password: str) -> int:
    request = urllib.request.Request(
        f"{endpoint.rstrip('/')}?{urllib.parse.urlencode({'query': query})}",
        headers={
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return int(response.read().decode().strip())


def _emit(index: int) -> EmittedTrace:
    marker = f"agentlens-private-{uuid4().hex}"
    tracer = trace.get_tracer("agentlens.pilot-acceptance")
    with tracer.start_as_current_span("agent.run") as root:
        root.set_attribute("input.value", f"private input {marker}")
        root.set_attribute("output.value", f"private output {marker}")
        root.set_attribute("gen_ai.prompt.0.content", f"alternate prompt {marker}")
        root.set_attribute("gen_ai.usage.input_tokens", 5 + index % 3)
        root.set_attribute("gen_ai.usage.output_tokens", 7 + index % 3)
        with tracer.start_as_current_span("pilot-tool") as child:
            child.set_attribute("tool.name", "pilot_acceptance")
            child.set_status(Status(StatusCode.OK))
        root.set_status(Status(StatusCode.OK))
        trace_id = f"{root.get_span_context().trace_id:032x}"
    return EmittedTrace(trace_id=trace_id, marker=marker, emitted_at=time.monotonic())


def _wait_for_executions(
    traces: list[EmittedTrace], *, api_url: str, deadline_seconds: float
) -> list[float]:
    pending = {item.trace_id: item for item in traces}
    latencies: list[float] = []
    deadline = time.monotonic() + deadline_seconds
    while pending and time.monotonic() < deadline:
        for trace_id, item in list(pending.items()):
            try:
                payload = _json(f"{api_url.rstrip('/')}/v1/executions/{trace_id}")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    continue
                raise
            if isinstance(payload, dict) and payload.get("trace_id") == trace_id:
                latencies.append(time.monotonic() - item.emitted_at)
                del pending[trace_id]
        if pending:
            time.sleep(0.5)
    if pending:
        sample = ", ".join(sorted(pending)[:3])
        raise RuntimeError(f"{len(pending)} traces missed freshness deadline; sample: {sample}")
    return latencies


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _verify_api_concurrency(api_url: str, concurrency: int) -> None:
    paths = ["/health/ready", "/v1/metrics/summary", "/v1/executions?limit=5"]
    urls = [f"{api_url.rstrip('/')}{paths[index % len(paths)]}" for index in range(concurrency)]
    with ThreadPoolExecutor(max_workers=min(concurrency, 32)) as executor:
        results = list(executor.map(_json, urls))
    if len(results) != concurrency:
        raise RuntimeError("concurrent API validation returned incomplete results")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--otlp-endpoint", default="http://localhost:4317")
    parser.add_argument("--api-url", default="http://localhost:18000")
    parser.add_argument("--clickhouse-url", default="http://localhost:18123")
    parser.add_argument("--clickhouse-user", default="agentlens")
    parser.add_argument("--clickhouse-password", default="change-me")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--traces-per-minute", type=float, default=1000)
    parser.add_argument("--deadline-seconds", type=float, default=60)
    parser.add_argument("--api-concurrency", type=int, default=30)
    args = parser.parse_args()
    if args.count < 1 or args.traces_per_minute <= 0 or args.api_concurrency < 1:
        parser.error("count, traces-per-minute, and api-concurrency must be positive")

    provider = instrument(
        framework="generic",
        agent_name="pilot-acceptance-agent",
        agent_version="1.0.0",
        environment="development",
        otlp_endpoint=args.otlp_endpoint,
        insecure=True,
    )
    interval = 60 / args.traces_per_minute
    emitted: list[EmittedTrace] = []
    try:
        for index in range(args.count):
            started = time.monotonic()
            emitted.append(_emit(index))
            remaining = interval - (time.monotonic() - started)
            if index + 1 < args.count and remaining > 0:
                time.sleep(remaining)
        provider.force_flush(timeout_millis=10_000)
    finally:
        provider.shutdown()

    latencies = _wait_for_executions(
        emitted, api_url=args.api_url, deadline_seconds=args.deadline_seconds
    )
    _verify_api_concurrency(args.api_url, args.api_concurrency)

    marker_predicate = " OR ".join(
        f"position(attributes_json, '{item.marker}') > 0" for item in emitted
    )
    leaked = _clickhouse_count(
        args.clickhouse_url,
        f"SELECT count() FROM agentlens.spans WHERE {marker_predicate}",
        username=args.clickhouse_user,
        password=args.clickhouse_password,
    )
    trace_ids = ",".join(repr(item.trace_id) for item in emitted)
    hashed = _clickhouse_count(
        args.clickhouse_url,
        "SELECT count() FROM agentlens.spans "
        f"WHERE trace_id IN ({trace_ids}) "
        "AND (length(input_hash) = 64 OR length(output_hash) = 64)",
        username=args.clickhouse_user,
        password=args.clickhouse_password,
    )
    if leaked:
        raise RuntimeError(f"privacy gate failed: {leaked} durable spans contain raw markers")
    if hashed < args.count:
        raise RuntimeError(f"privacy gate failed: only {hashed} traces retained content HMACs")

    print(
        json.dumps(
            {
                "status": "passed",
                "traces": len(emitted),
                "p95_freshness_seconds": round(_p95(latencies), 3),
                "durable_raw_content_matches": leaked,
                "durable_hashed_spans": hashed,
                "api_concurrency": args.api_concurrency,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
