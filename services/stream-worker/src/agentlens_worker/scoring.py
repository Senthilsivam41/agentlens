"""Mathematical drift and ambiguity scoring."""

from __future__ import annotations

import math
from uuid import UUID, uuid5

import numpy as np
from agentlens_contracts import (
    ExecutionFeatures,
    ExecutionScore,
    Finding,
    FindingSeverity,
    RootCause,
    SamplingDecision,
    ScoreStatus,
)

from .baseline import BaselineArtifact, _path_vector

SCORE_NAMESPACE = UUID("dc7ef830-c4f2-48ea-a568-1da366316961")
FINDING_NAMESPACE = UUID("5547f7b9-56b1-4a33-98dd-3324750436e9")


def _score_id(features: ExecutionFeatures, discriminator: str) -> UUID:
    return uuid5(
        SCORE_NAMESPACE,
        f"{features.tenant_id}:{features.cluster_id}:{features.trace_id}:{discriminator}",
    )


def score_execution(
    *,
    features: ExecutionFeatures,
    sampling: SamplingDecision,
    baseline: BaselineArtifact,
    input_embedding: list[float],
    output_embedding: list[float],
) -> ExecutionScore:
    dimensions_match = (
        len(input_embedding) == baseline.embedding_dimensions
        and len(output_embedding) == baseline.embedding_dimensions
    )
    if not dimensions_match:
        raise ValueError("embedding dimension does not match baseline")
    output = np.asarray(output_embedding, dtype=float)
    projected = (output - np.asarray(baseline.pca_mean)) @ np.asarray(baseline.pca_components).T
    path = np.asarray(_path_vector(features.tool_path, baseline.tool_vocabulary))
    trajectory = np.concatenate([projected, path])
    delta = trajectory - np.asarray(baseline.mean_vector)
    quadratic = float(delta @ np.asarray(baseline.inverse_covariance) @ delta.T)
    distance = math.sqrt(max(0.0, quadratic))
    ambiguity = _ambiguity(
        entropy=features.input_entropy or 0,
        input_embedding=np.asarray(input_embedding),
        centroids=np.asarray(baseline.intent_centroids),
        alpha=baseline.ambiguity_alpha,
    )
    drifted = distance > baseline.drift_threshold
    volatility = features.trajectory_volatility or 0
    cause, rationale = _classify(
        drifted=drifted,
        distance=distance,
        ambiguity=ambiguity,
        ambiguity_threshold=baseline.ambiguity_threshold,
        volatility=volatility,
        errors=features.error_count,
        timeouts=features.timeout_count,
    )
    return ExecutionScore(
        score_id=_score_id(features, f"semantic:{baseline.baseline_id}:metrics.v1"),
        tenant_id=features.tenant_id,
        cluster_id=features.cluster_id,
        trace_id=features.trace_id,
        baseline_id=UUID(baseline.baseline_id),
        status=ScoreStatus.COMPLETE,
        sampling=sampling,
        mahalanobis_distance=distance,
        ambiguity_score=ambiguity,
        trajectory_volatility=volatility,
        drift_threshold=baseline.drift_threshold,
        ambiguity_threshold=baseline.ambiguity_threshold,
        is_drifted=drifted,
        root_cause=cause,
        rationale=rationale,
    )


def structural_score(*, features: ExecutionFeatures, sampling: SamplingDecision) -> ExecutionScore:
    volatility = features.trajectory_volatility or 0
    if features.timeout_count or features.error_count:
        cause = RootCause.TOOL_RUNTIME_FAILURE
        rationale = ["execution contains error or timeout spans"]
    elif volatility >= 4:
        cause = RootCause.HIGH_VOLATILITY
        rationale = ["trajectory volatility exceeds structural threshold"]
    else:
        cause = RootCause.INSUFFICIENT_EVIDENCE
        rationale = ["semantic scoring was not selected"]
    return ExecutionScore(
        score_id=_score_id(features, "structural:metrics.v1"),
        tenant_id=features.tenant_id,
        cluster_id=features.cluster_id,
        trace_id=features.trace_id,
        status=ScoreStatus.STRUCTURAL_ONLY if sampling.selected else ScoreStatus.NOT_SAMPLED,
        sampling=sampling,
        trajectory_volatility=volatility,
        root_cause=cause,
        rationale=rationale,
    )


def unavailable_score(
    *,
    features: ExecutionFeatures,
    sampling: SamplingDecision,
    status: ScoreStatus,
    rationale: str,
) -> ExecutionScore:
    """Produce an idempotent terminal score without retaining sensitive input."""

    return ExecutionScore(
        score_id=_score_id(features, f"semantic:{status.value}:metrics.v1"),
        tenant_id=features.tenant_id,
        cluster_id=features.cluster_id,
        trace_id=features.trace_id,
        status=status,
        sampling=sampling,
        trajectory_volatility=features.trajectory_volatility,
        root_cause=RootCause.INSUFFICIENT_EVIDENCE,
        rationale=[rationale],
    )


def finding_from_score(score: ExecutionScore) -> Finding | None:
    """Create one deterministic finding for actionable classifications."""

    severity_by_cause = {
        RootCause.TOOL_RUNTIME_FAILURE: FindingSeverity.CRITICAL,
        RootCause.AGENT_LOGIC_FAILURE: FindingSeverity.HIGH,
        RootCause.USER_PROMPT_AMBIGUITY: FindingSeverity.MEDIUM,
        RootCause.HIGH_VOLATILITY: FindingSeverity.MEDIUM,
    }
    severity = severity_by_cause.get(score.root_cause)
    if severity is None:
        return None
    titles = {
        RootCause.TOOL_RUNTIME_FAILURE: "Tool runtime failure detected",
        RootCause.AGENT_LOGIC_FAILURE: "Agent behavior drift detected",
        RootCause.USER_PROMPT_AMBIGUITY: "Ambiguous input associated with drift",
        RootCause.HIGH_VOLATILITY: "High execution-path volatility detected",
    }
    return Finding(
        finding_id=uuid5(FINDING_NAMESPACE, str(score.score_id)),
        tenant_id=score.tenant_id,
        cluster_id=score.cluster_id,
        trace_id=score.trace_id,
        score_id=score.score_id,
        severity=severity,
        root_cause=score.root_cause,
        title=titles[score.root_cause],
        rationale=score.rationale,
    )


def _ambiguity(
    *, entropy: float, input_embedding: np.ndarray, centroids: np.ndarray, alpha: float
) -> float:
    if centroids.size == 0:
        return entropy
    input_norm = np.linalg.norm(input_embedding)
    centroid_norms = np.linalg.norm(centroids, axis=1)
    denominators = np.maximum(input_norm * centroid_norms, 1e-12)
    similarities = centroids @ input_embedding / denominators
    dispersion = 1 - float(np.mean(similarities))
    return max(0, entropy + alpha * dispersion)


def _classify(
    *,
    drifted: bool,
    distance: float,
    ambiguity: float,
    ambiguity_threshold: float,
    volatility: float,
    errors: int,
    timeouts: int,
) -> tuple[RootCause, list[str]]:
    if errors or timeouts:
        return RootCause.TOOL_RUNTIME_FAILURE, ["execution contains error or timeout spans"]
    if drifted and ambiguity > ambiguity_threshold:
        return RootCause.USER_PROMPT_AMBIGUITY, [
            f"trajectory distance {distance:.3f} exceeds baseline threshold",
            f"ambiguity {ambiguity:.3f} exceeds calibrated threshold",
        ]
    if drifted:
        return RootCause.AGENT_LOGIC_FAILURE, [
            f"trajectory distance {distance:.3f} exceeds baseline threshold",
            "input ambiguity remains below calibrated threshold",
        ]
    if volatility >= 4:
        return RootCause.HIGH_VOLATILITY, ["trajectory volatility exceeds structural threshold"]
    return RootCause.COMPLIANT, ["trajectory remains within calibrated baseline"]
