"""Convert transient spans into text-free durable records."""

import json

from agentlens_contracts import DurableSpan, TransientSpan

from .hashing import content_hmac

# Semantic-convention providers use several names for prompt and response
# content. Keep operational metadata, but discard content-bearing attributes at
# the last boundary before durable storage. This is defense in depth: callers
# cannot accidentally persist raw content by constructing a TransientSpan
# directly or by adding a new normalizer alias.
_CONTENT_ATTRIBUTE_KEYS = frozenset(
    {
        "input.value",
        "output.value",
        "openinference.input.value",
        "openinference.output.value",
        "llm.input_messages",
        "llm.output_messages",
        "gen_ai.prompt",
        "gen_ai.completion",
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.system_instructions",
    }
)
_CONTENT_ATTRIBUTE_PREFIXES = (
    "gen_ai.prompt.",
    "gen_ai.completion.",
    "gen_ai.input.messages.",
    "gen_ai.output.messages.",
    "llm.prompts.",
    "llm.completions.",
)


def durable_attributes(attributes: dict[str, object]) -> dict[str, object]:
    """Return operational attributes with all known content fields removed."""
    return {
        key: value
        for key, value in attributes.items()
        if key.lower() not in _CONTENT_ATTRIBUTE_KEYS
        and not key.lower().startswith(_CONTENT_ATTRIBUTE_PREFIXES)
    }


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
        attributes_json=json.dumps(
            durable_attributes(span.attributes), separators=(",", ":"), sort_keys=True
        ),
    )
