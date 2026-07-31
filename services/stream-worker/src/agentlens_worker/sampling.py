"""Versioned adaptive semantic sampling policy."""

from __future__ import annotations

import hashlib

from agentlens_contracts import ExecutionFeatures, SamplingDecision, SamplingReason


class AdaptiveSampler:
    def __init__(self, *, normal_sample_rate: float = 0.1, volatility_threshold: float = 4) -> None:
        if not 0 <= normal_sample_rate <= 1:
            raise ValueError("normal_sample_rate must be between 0 and 1")
        self._normal_sample_rate = normal_sample_rate
        self._volatility_threshold = volatility_threshold

    def decide(
        self,
        features: ExecutionFeatures,
        *,
        known_tool_paths: set[tuple[str, ...]] | None = None,
        known_agent_versions: set[str] | None = None,
    ) -> SamplingDecision:
        if features.error_count or features.timeout_count:
            return self._selected(SamplingReason.ERROR)
        if (features.trajectory_volatility or 0) >= self._volatility_threshold:
            return self._selected(SamplingReason.HIGH_VOLATILITY)
        path = tuple(features.tool_path)
        if known_tool_paths is not None and path not in known_tool_paths:
            return self._selected(SamplingReason.UNKNOWN_PATH)
        if known_agent_versions is not None and features.agent_version not in known_agent_versions:
            return self._selected(SamplingReason.NEW_VERSION)
        bucket = int(hashlib.sha256(features.trace_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if bucket < self._normal_sample_rate:
            return self._selected(SamplingReason.DETERMINISTIC_NORMAL)
        return SamplingDecision(
            selected=False,
            reason=SamplingReason.NOT_SELECTED,
            normal_sample_rate=self._normal_sample_rate,
        )

    def _selected(self, reason: SamplingReason) -> SamplingDecision:
        return SamplingDecision(
            selected=True,
            reason=reason,
            normal_sample_rate=self._normal_sample_rate,
        )
