"""Run local Redpanda replay, duplicate, and edge-queue recovery acceptance gates."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agentlens import instrument
from aiokafka import AIOKafkaProducer
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Status
from opentelemetry.sdk.trace import TracerProvider

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "infra/compose/docker-compose.yaml"
_EDGE_PROVIDER: TracerProvider | None = None


@dataclass(frozen=True, slots=True)
class TraceFixture:
    trace_id: str
    payload: bytes
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


class Compose:
    def __init__(self, env_file: Path) -> None:
        self.env_file = env_file

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = [
            "docker",
            "compose",
            "--env-file",
            str(self.env_file),
            "-f",
            str(COMPOSE_FILE),
            *args,
        ]
        return subprocess.run(command, cwd=ROOT, check=check, text=True, capture_output=True)

    def queue_state(self, metrics_url: str) -> tuple[int, str]:
        with urllib.request.urlopen(metrics_url, timeout=10) as response:
            metrics = response.read().decode()
        queue_size = 0
        for line in metrics.splitlines():
            if (
                line.startswith("otelcol_exporter_queue_size{")
                and 'exporter="otlp_grpc/platform"' in line
            ):
                queue_size = int(float(line.rsplit(" ", 1)[1]))
                break
        result = self.run(
            "run",
            "--rm",
            "--no-deps",
            "edge-queue-init",
            "sh",
            "-ec",
            "sha256sum /var/lib/otelcol/exporter_otlp_grpc_platform_traces",
        )
        digest = result.stdout.strip().split()[0]
        return queue_size, digest


def _raw_otlp_fixture(*, tenant: str, cluster: str, trace_id: str) -> TraceFixture:
    now_ns = time.time_ns()
    request = ExportTraceServiceRequest()
    resource_spans = request.resource_spans.add()
    resource_spans.resource.attributes.extend(
        [
            KeyValue(key="agentlens.tenant_id", value=AnyValue(string_value=tenant)),
            KeyValue(key="agentlens.cluster_id", value=AnyValue(string_value=cluster)),
            KeyValue(key="service.name", value=AnyValue(string_value="recovery-agent")),
            KeyValue(key="deployment.environment.name", value=AnyValue(string_value="development")),
            KeyValue(key="agentlens.agent.name", value=AnyValue(string_value="recovery-agent")),
            KeyValue(key="agentlens.agent.version", value=AnyValue(string_value="1.0.0")),
            KeyValue(key="agentlens.framework", value=AnyValue(string_value="generic")),
        ]
    )
    scope_spans = resource_spans.scope_spans.add()
    root = scope_spans.spans.add()
    root.trace_id = bytes.fromhex(trace_id)
    root.span_id = bytes.fromhex("a" * 16)
    root.name = "agent.run"
    root.start_time_unix_nano = now_ns
    root.end_time_unix_nano = now_ns + 1_000_000
    root.status.code = Status.STATUS_CODE_OK
    root.attributes.extend(
        [
            KeyValue(key="input.value", value=AnyValue(string_value="recovery input")),
            KeyValue(key="output.value", value=AnyValue(string_value="recovery output")),
            KeyValue(key="gen_ai.usage.input_tokens", value=AnyValue(int_value=3)),
            KeyValue(key="gen_ai.usage.output_tokens", value=AnyValue(int_value=4)),
        ]
    )
    child = scope_spans.spans.add()
    child.trace_id = bytes.fromhex(trace_id)
    child.span_id = bytes.fromhex("b" * 16)
    child.parent_span_id = bytes.fromhex("a" * 16)
    child.name = "recovery-tool"
    child.start_time_unix_nano = now_ns + 100_000
    child.end_time_unix_nano = now_ns + 900_000
    child.status.code = Status.STATUS_CODE_OK
    child.attributes.add(key="tool.name", value=AnyValue(string_value="recovery-tool"))
    return TraceFixture(
        trace_id=trace_id, payload=request.SerializeToString(), emitted_at=time.monotonic()
    )


async def _publish_duplicate(fixture: TraceFixture, bootstrap: str, topic: str) -> None:
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap, acks="all")
    await producer.start()
    try:
        for _ in range(2):
            await producer.send_and_wait(topic, fixture.payload, key=fixture.trace_id.encode())
    finally:
        await producer.stop()


def _emit_through_edge(endpoint: str) -> TraceFixture:
    global _EDGE_PROVIDER
    if _EDGE_PROVIDER is None:
        _EDGE_PROVIDER = instrument(
            framework="generic",
            agent_name="edge-recovery-agent",
            agent_version="1.0.0",
            environment="development",
            otlp_endpoint=endpoint,
            insecure=True,
        )
    tracer = trace.get_tracer("agentlens.recovery")
    with tracer.start_as_current_span("agent.run") as root:
        root.set_attribute("input.value", "edge buffered input")
        root.set_attribute("output.value", "edge buffered output")
        with tracer.start_as_current_span("buffered-tool"):
            pass
        trace_id = f"{root.get_span_context().trace_id:032x}"
    _EDGE_PROVIDER.force_flush(timeout_millis=10_000)
    return TraceFixture(trace_id=trace_id, payload=b"", emitted_at=time.monotonic())


def _shutdown_edge_provider() -> None:
    if _EDGE_PROVIDER is not None:
        _EDGE_PROVIDER.shutdown()


def _wait_for_execution(api_url: str, trace_id: str, deadline: float) -> float:
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            payload = _json(f"{api_url.rstrip('/')}/v1/executions/{trace_id}")
            if isinstance(payload, dict) and payload.get("trace_id") == trace_id:
                return time.monotonic()
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(0.5)
    raise TimeoutError(f"execution {trace_id} did not become queryable within {deadline}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--api-url", default="http://localhost:18000")
    parser.add_argument("--edge-endpoint", default="http://localhost:4317")
    parser.add_argument("--edge-metrics-url", default="http://localhost:18889/metrics")
    parser.add_argument("--clickhouse-url", default="http://localhost:18123")
    parser.add_argument("--clickhouse-user", default="agentlens")
    parser.add_argument(
        "--clickhouse-password", default=os.getenv("CLICKHOUSE_PASSWORD", "change-me")
    )
    parser.add_argument("--kafka-bootstrap", default="localhost:19092")
    parser.add_argument("--raw-topic", default="agentlens.otlp.traces.v1")
    parser.add_argument("--deadline-seconds", type=float, default=90)
    args = parser.parse_args()
    env_file = ROOT / args.env_file
    if not env_file.is_file():
        env_file = ROOT / ".env.example"
    compose = Compose(env_file)

    compose.run(
        "up",
        "-d",
        "clickhouse",
        "redpanda",
        "migrations",
        "topics",
        "otel-platform",
        "otel-edge",
        "worker-normalize",
        "worker-assemble",
        "api",
    )

    queue_before, queue_digest_before = compose.queue_state(args.edge_metrics_url)
    platform_stopped = False
    redpanda_stopped = False
    workers_stopped = False
    try:
        compose.run("stop", "otel-platform")
        platform_stopped = True
        edge_fixture = _emit_through_edge(args.edge_endpoint)
        time.sleep(5)
        queue_during_outage, queue_digest_during = compose.queue_state(args.edge_metrics_url)
        compose.run("start", "otel-platform")
        platform_stopped = False
        edge_completed_at = _wait_for_execution(
            args.api_url, edge_fixture.trace_id, args.deadline_seconds
        )

        compose.run("stop", "redpanda")
        redpanda_stopped = True
        redpanda_fixture = _emit_through_edge(args.edge_endpoint)
        time.sleep(5)
        compose.run("start", "redpanda")
        redpanda_stopped = False
        redpanda_completed_at = _wait_for_execution(
            args.api_url, redpanda_fixture.trace_id, args.deadline_seconds
        )

        compose.run("stop", "worker-normalize", "worker-assemble")
        workers_stopped = True
        duplicate_fixture = _raw_otlp_fixture(
            tenant="local", cluster="local-compose", trace_id=uuid4().hex
        )
        asyncio.run(_publish_duplicate(duplicate_fixture, args.kafka_bootstrap, args.raw_topic))
        compose.run("start", "worker-normalize", "worker-assemble")
        workers_stopped = False
        duplicate_completed_at = _wait_for_execution(
            args.api_url, duplicate_fixture.trace_id, args.deadline_seconds
        )
        final_count = _clickhouse_count(
            args.clickhouse_url,
            "SELECT count() FROM agentlens.executions FINAL "
            f"WHERE tenant_id='local' AND trace_id='{duplicate_fixture.trace_id}'",
            username=args.clickhouse_user,
            password=args.clickhouse_password,
        )
        span_count = _clickhouse_count(
            args.clickhouse_url,
            "SELECT count() FROM agentlens.spans FINAL "
            f"WHERE tenant_id='local' AND trace_id='{duplicate_fixture.trace_id}'",
            username=args.clickhouse_user,
            password=args.clickhouse_password,
        )
        if final_count != 1 or span_count != 2:
            raise RuntimeError(
                "duplicate replay gate failed: "
                f"executions={final_count}, durable_spans={span_count}"
            )
        if queue_during_outage <= queue_before or queue_during_outage == 0:
            raise RuntimeError(
                "edge disk queue did not grow during platform outage: "
                f"before={queue_before}, during={queue_during_outage}"
            )
        if queue_digest_during == queue_digest_before:
            raise RuntimeError("edge persistent queue file did not change during platform outage")

        print(
            json.dumps(
                {
                    "status": "passed",
                    "edge_trace_id": edge_fixture.trace_id,
                    "edge_queue_batches_before": queue_before,
                    "edge_queue_batches_during_outage": queue_during_outage,
                    "edge_queue_file_changed": queue_digest_during != queue_digest_before,
                    "edge_replay_seconds": round(edge_completed_at - edge_fixture.emitted_at, 3),
                    "redpanda_trace_id": redpanda_fixture.trace_id,
                    "redpanda_replay_seconds": round(
                        redpanda_completed_at - redpanda_fixture.emitted_at, 3
                    ),
                    "duplicate_trace_id": duplicate_fixture.trace_id,
                    "duplicate_replay_seconds": round(
                        duplicate_completed_at - duplicate_fixture.emitted_at, 3
                    ),
                    "final_executions": final_count,
                    "final_durable_spans": span_count,
                },
                sort_keys=True,
            )
        )
    finally:
        if platform_stopped:
            compose.run("start", "otel-platform", check=False)
        if redpanda_stopped:
            compose.run("start", "redpanda", check=False)
        if workers_stopped:
            compose.run("start", "worker-normalize", "worker-assemble", check=False)
        _shutdown_edge_provider()


if __name__ == "__main__":
    main()
