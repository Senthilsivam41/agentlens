"""Convert transient spans into text-free durable records."""

from __future__ import annotations

import json

from agentlens_contracts import DurableSpan, TransientSpan

from .hashing import content_hmac


def to_durable(span: TransientSpan, *, hmac_key: bytes) -> DurableSpan:
    input_value = span.input_text.get_secret_value() if span.input_text else None
    output_value = span.output_text.get_secret_value() if span.output_text else None
    return DurableSpan(
        schema_version=span.schema_version,
        event_id=span.event_id,
        tenant_id=span.tenant_id,
        cluster_id=span.cluster_id,
        cloud_provider=span.cloud_provider,
        cloud_region=span.cloud_region,
        environment=span.environment,
        service_name=span.service_name,
        agent_name=span.agent_name,
        agent_version=span.agent_version,
        framework=span.framework,
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        span_name=span.span_name,
        started_at=span.started_at,
        ended_at=span.ended_at,
        duration_ms=span.duration_ms,
        status=span.status,
        graph_node=span.graph_node,
        tool_name=span.tool_name,
        model_name=span.model_name,
        prompt_tokens=span.prompt_tokens,
        completion_tokens=span.completion_tokens,
        retry_count=span.retry_count,
        input_hash=content_hmac(input_value, hmac_key),
        output_hash=content_hmac(output_value, hmac_key),
        attributes_json=json.dumps(span.attributes, separators=(",", ":"), sort_keys=True),
    )
