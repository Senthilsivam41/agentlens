"""Deterministic trace feature extraction and volatility scoring."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from agentlens_contracts import DataQuality, ExecutionFeatures, SpanStatus, TransientSpan

from .hashing import content_hmac


@dataclass(frozen=True, slots=True)
class VolatilityConfig:
    baseline_steps: float = 5
    baseline_tokens: float = 1000
    step_weight: float = 1
    token_weight: float = 1
    retry_weight: float = 1


def shannon_entropy(value: str | None) -> float | None:
    if not value:
        return None
    tokens = value.casefold().split()
    if not tokens:
        return None
    counts = Counter(tokens)
    total = len(tokens)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def extract_features(
    spans: list[TransientSpan], *, hmac_key: bytes, config: VolatilityConfig | None = None
) -> ExecutionFeatures:
    if not spans:
        raise ValueError("cannot extract features from an empty trace")
    selected_config = config or VolatilityConfig()
    ordered = sorted(spans, key=lambda item: (item.started_at, item.span_id))
    roots = [span for span in ordered if span.parent_span_id is None]
    root = roots[0] if roots else ordered[0]
    tool_spans = [span for span in ordered if span.tool_name]
    retry_counts: Counter[str] = Counter()
    for span in tool_spans:
        retry_counts[span.tool_name or "unknown"] += span.retry_count
    total_tokens = sum(span.prompt_tokens + span.completion_tokens for span in ordered)
    total_retries = sum(span.retry_count for span in ordered)
    step_count = len(ordered)
    volatility = (
        selected_config.step_weight * (step_count / max(selected_config.baseline_steps, 1)) ** 2
        + selected_config.token_weight * (total_tokens / max(selected_config.baseline_tokens, 1))
        + selected_config.retry_weight * sum(count**2 for count in retry_counts.values())
    )
    input_value = root.input_text.get_secret_value() if root.input_text else None
    output_value = root.output_text.get_secret_value() if root.output_text else None
    return ExecutionFeatures(
        tenant_id=root.tenant_id,
        cluster_id=root.cluster_id,
        trace_id=root.trace_id,
        environment=root.environment,
        agent_name=root.agent_name,
        agent_version=root.agent_version,
        started_at=min(span.started_at for span in ordered),
        ended_at=max(span.ended_at for span in ordered),
        data_quality=DataQuality.COMPLETE if roots else DataQuality.INCOMPLETE,
        step_count=step_count,
        total_tokens=total_tokens,
        duration_ms=(
            max(span.ended_at for span in ordered) - min(span.started_at for span in ordered)
        ).total_seconds()
        * 1000,
        total_retries=total_retries,
        error_count=sum(span.status == SpanStatus.ERROR for span in ordered),
        timeout_count=sum(span.status == SpanStatus.TIMEOUT for span in ordered),
        tool_path=[span.tool_name for span in tool_spans if span.tool_name],
        tool_retry_counts=dict(retry_counts),
        input_hash=content_hmac(input_value, hmac_key),
        output_hash=content_hmac(output_value, hmac_key),
        input_entropy=shannon_entropy(input_value),
        trajectory_volatility=volatility,
    )
