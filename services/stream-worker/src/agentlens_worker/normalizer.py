"""Convert OTLP protobuf trace batches into the canonical transient span contract."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from agentlens_contracts import CloudProvider, Framework, SpanStatus, TransientSpan
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Span
from pydantic import SecretStr

from .hashing import event_id
from .redaction import redact_text


class NormalizationError(ValueError):
    """Raised when an OTLP batch cannot satisfy the Agent Lens contract."""


def _value(value: AnyValue) -> Any:
    selected = value.WhichOneof("value")
    if selected == "string_value":
        return value.string_value
    if selected == "bool_value":
        return value.bool_value
    if selected == "int_value":
        return value.int_value
    if selected == "double_value":
        return value.double_value
    if selected == "bytes_value":
        return value.bytes_value.hex()
    if selected == "array_value":
        return [_value(item) for item in value.array_value.values]
    if selected == "kvlist_value":
        return {item.key: _value(item.value) for item in value.kvlist_value.values}
    return None


def _attributes(values: Iterable[KeyValue]) -> dict[str, Any]:
    return {item.key: _value(item.value) for item in values}


def _text(attributes: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if isinstance(value, str):
            return redact_text(value)
    return None


def _integer(attributes: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = attributes.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0, int(value))
    return 0


def _status(span: Span, attributes: dict[str, Any]) -> SpanStatus:
    error_type = str(attributes.get("error.type", "")).lower()
    if "timeout" in error_type:
        return SpanStatus.TIMEOUT
    if span.status.code == 2:
        return SpanStatus.ERROR
    if span.status.code == 1:
        return SpanStatus.OK
    return SpanStatus.UNSET


def _framework(value: object) -> Framework:
    try:
        return Framework(str(value).lower())
    except ValueError:
        return Framework.GENERIC


def _cloud_provider(value: object) -> CloudProvider:
    aliases = {"aks": "azure", "azure": "azure", "eks": "aws", "aws": "aws"}
    try:
        return CloudProvider(aliases.get(str(value).lower(), str(value).lower()))
    except ValueError:
        return CloudProvider.UNKNOWN


class OtlpNormalizer:
    def normalize(self, payload: bytes) -> list[TransientSpan]:
        request = ExportTraceServiceRequest()
        try:
            request.ParseFromString(payload)
        except Exception as exc:  # protobuf raises implementation-specific DecodeError
            raise NormalizationError("invalid OTLP protobuf payload") from exc
        normalized: list[TransientSpan] = []
        for resource_spans in request.resource_spans:
            resource = _attributes(resource_spans.resource.attributes)
            for scope_spans in resource_spans.scope_spans:
                for span in scope_spans.spans:
                    normalized.append(self._span(resource, _attributes(span.attributes), span))
        if not normalized:
            raise NormalizationError("OTLP payload contains no spans")
        return normalized

    def _span(
        self, resource: dict[str, Any], attributes: dict[str, Any], span: Span
    ) -> TransientSpan:
        tenant_id = str(resource.get("agentlens.tenant_id", "")).strip()
        cluster_id = str(resource.get("agentlens.cluster_id", "")).strip()
        if not tenant_id or not cluster_id:
            raise NormalizationError("tenant and cluster identity are required")
        trace_id = span.trace_id.hex()
        span_id = span.span_id.hex()
        parent_span_id = span.parent_span_id.hex() or None
        started_at = datetime.fromtimestamp(span.start_time_unix_nano / 1e9, tz=UTC)
        ended_at = datetime.fromtimestamp(span.end_time_unix_nano / 1e9, tz=UTC)
        framework = _framework(resource.get("agentlens.framework", "generic"))
        return TransientSpan(
            event_id=event_id(
                tenant_id,
                cluster_id,
                trace_id,
                span_id,
                str(span.start_time_unix_nano),
            ),
            tenant_id=tenant_id,
            cluster_id=cluster_id,
            cloud_provider=_cloud_provider(resource.get("cloud.provider", "unknown")),
            cloud_region=str(resource["cloud.region"]) if resource.get("cloud.region") else None,
            environment=str(resource.get("deployment.environment.name", "unknown")),
            service_name=str(resource.get("service.name", "unknown-service")),
            agent_name=str(
                resource.get(
                    "agentlens.agent.name",
                    resource.get("service.name", "unknown"),
                )
            ),
            agent_version=str(resource.get("agentlens.agent.version", "unknown")),
            framework=framework,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            span_name=span.name or "unnamed-span",
            started_at=started_at,
            ended_at=ended_at,
            status=_status(span, attributes),
            graph_node=_text(attributes, "graph.node.name", "agent.graph.node"),
            tool_name=_text(attributes, "tool.name", "openinference.tool.name"),
            model_name=_text(attributes, "llm.model_name", "gen_ai.request.model"),
            prompt_tokens=_integer(
                attributes, "llm.token_count.prompt", "gen_ai.usage.input_tokens"
            ),
            completion_tokens=_integer(
                attributes, "llm.token_count.completion", "gen_ai.usage.output_tokens"
            ),
            retry_count=_integer(attributes, "agentlens.retry_count", "tool.retry_count"),
            input_text=_secret_text(attributes, "input.value", "openinference.input.value"),
            output_text=_secret_text(attributes, "output.value", "openinference.output.value"),
            attributes=attributes,
        )


def _secret_text(attributes: dict[str, Any], *keys: str) -> SecretStr | None:
    value = _text(attributes, *keys)
    return SecretStr(value) if value is not None else None
