from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
from agentlens_contracts import (
    DataQuality,
    ExecutionFeatures,
    RootCause,
    SamplingDecision,
    SamplingReason,
)
from agentlens_worker.baseline import BaselineArtifact
from agentlens_worker.scoring import finding_from_score, score_execution


def test_score_classifies_drift_with_low_ambiguity_as_logic_failure() -> None:
    baseline = BaselineArtifact(
        baseline_id=str(uuid4()),
        embedding_model="test",
        embedding_dimensions=2,
        pca_mean=[0, 0],
        pca_components=[[1, 0], [0, 1]],
        tool_vocabulary=[],
        mean_vector=[0, 0, 0],
        inverse_covariance=np.eye(3).tolist(),
        intent_centroids=[[1, 0]],
        distance_mean=0,
        distance_stddev=0.1,
        drift_threshold=1,
        ambiguity_threshold=2,
    )
    now = datetime(2026, 7, 31, tzinfo=UTC)
    features = ExecutionFeatures(
        tenant_id="tenant",
        cluster_id="cluster",
        trace_id="a" * 32,
        environment="test",
        agent_name="agent",
        agent_version="1",
        started_at=now,
        ended_at=now,
        data_quality=DataQuality.COMPLETE,
        step_count=1,
        total_tokens=1,
        duration_ms=1,
        total_retries=0,
        error_count=0,
        timeout_count=0,
        input_entropy=0,
        trajectory_volatility=0,
    )
    score = score_execution(
        features=features,
        sampling=SamplingDecision(selected=True, reason=SamplingReason.NEW_VERSION),
        baseline=baseline,
        input_embedding=[1, 0],
        output_embedding=[3, 0],
    )
    assert score.is_drifted
    assert score.root_cause == RootCause.AGENT_LOGIC_FAILURE
    assert finding_from_score(score) is not None

    repeated = score_execution(
        features=features,
        sampling=SamplingDecision(selected=True, reason=SamplingReason.NEW_VERSION),
        baseline=baseline,
        input_embedding=[1, 0],
        output_embedding=[3, 0],
    )
    assert repeated.score_id == score.score_id
