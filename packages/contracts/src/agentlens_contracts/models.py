"""Versioned contracts shared by ingestion, analytics, API, and SDK packages."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class Framework(StrEnum):
    LANGGRAPH = "langgraph"
    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    ADK = "adk"
    GENERIC = "generic"


class CloudProvider(StrEnum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    ON_PREM = "on-prem"
    UNKNOWN = "unknown"


class SpanStatus(StrEnum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class DataQuality(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


class SamplingReason(StrEnum):
    ERROR = "error"
    HIGH_VOLATILITY = "high_volatility"
    UNKNOWN_PATH = "unknown_path"
    NEW_VERSION = "new_version"
    DETERMINISTIC_NORMAL = "deterministic_normal"
    NOT_SELECTED = "not_selected"


class ScoreStatus(StrEnum):
    COMPLETE = "complete"
    STRUCTURAL_ONLY = "structural_only"
    NOT_SAMPLED = "not_sampled"
    INSUFFICIENT_BASELINE = "insufficient_baseline"
    EMBEDDING_UNAVAILABLE = "embedding_unavailable"
    INVALID_INPUT = "invalid_input"


class RootCause(StrEnum):
    COMPLIANT = "compliant"
    USER_PROMPT_AMBIGUITY = "user_prompt_ambiguity"
    AGENT_LOGIC_FAILURE = "agent_logic_failure"
    TOOL_RUNTIME_FAILURE = "tool_runtime_failure"
    HIGH_VOLATILITY = "high_volatility"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TransientSpan(ContractModel):
    """Transient normalized span. Text fields must never enter durable storage."""

    schema_version: str = Field(default="agentlens.span.v1", pattern=r"^agentlens\.span\.v1$")
    event_id: str = Field(min_length=16, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    cluster_id: str = Field(min_length=1, max_length=128)
    cloud_provider: CloudProvider = CloudProvider.UNKNOWN
    cloud_region: str | None = Field(default=None, max_length=128)
    environment: str = Field(min_length=1, max_length=64)
    service_name: str = Field(min_length=1, max_length=256)
    agent_name: str = Field(min_length=1, max_length=256)
    agent_version: str = Field(min_length=1, max_length=128)
    framework: Framework = Framework.GENERIC
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    parent_span_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    span_name: str = Field(min_length=1, max_length=512)
    started_at: datetime
    ended_at: datetime
    status: SpanStatus = SpanStatus.UNSET
    graph_node: str | None = Field(default=None, max_length=256)
    tool_name: str | None = Field(default=None, max_length=256)
    model_name: str | None = Field(default=None, max_length=256)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0, le=65535)
    input_text: SecretStr | None = None
    output_text: SecretStr | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("started_at", "ended_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        return self

    @property
    def duration_ms(self) -> float:
        return (self.ended_at - self.started_at).total_seconds() * 1000


class DurableSpan(ContractModel):
    schema_version: str = "agentlens.span.v1"
    event_id: str
    tenant_id: str
    cluster_id: str
    cloud_provider: CloudProvider
    cloud_region: str | None = None
    environment: str
    service_name: str
    agent_name: str
    agent_version: str
    framework: Framework
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    span_name: str
    started_at: datetime
    ended_at: datetime
    duration_ms: float = Field(ge=0)
    status: SpanStatus
    graph_node: str | None = None
    tool_name: str | None = None
    model_name: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retry_count: int = 0
    input_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    output_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    attributes_json: str = "{}"


class ExecutionFeatures(ContractModel):
    feature_version: str = "features.v1"
    tenant_id: str
    cluster_id: str
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    environment: str
    agent_name: str
    agent_version: str
    started_at: datetime
    ended_at: datetime
    data_quality: DataQuality
    step_count: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    total_retries: int = Field(ge=0)
    error_count: int = Field(ge=0)
    timeout_count: int = Field(ge=0)
    tool_path: list[str] = Field(default_factory=list)
    tool_retry_counts: dict[str, int] = Field(default_factory=dict)
    input_hash: str | None = None
    output_hash: str | None = None
    input_entropy: float | None = Field(default=None, ge=0)
    trajectory_volatility: float | None = Field(default=None, ge=0)


class SamplingDecision(ContractModel):
    policy_version: str = "adaptive.v1"
    selected: bool
    reason: SamplingReason
    normal_sample_rate: float = Field(default=0.1, ge=0, le=1)


class ExecutionScore(ContractModel):
    score_id: UUID
    tenant_id: str
    cluster_id: str
    trace_id: str
    baseline_id: UUID | None = None
    metric_version: str = "metrics.v1"
    status: ScoreStatus
    sampling: SamplingDecision
    mahalanobis_distance: float | None = Field(default=None, ge=0)
    ambiguity_score: float | None = Field(default=None, ge=0)
    trajectory_volatility: float | None = Field(default=None, ge=0)
    drift_threshold: float | None = Field(default=None, ge=0)
    ambiguity_threshold: float | None = Field(default=None, ge=0)
    is_drifted: bool | None = None
    root_cause: RootCause
    rationale: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaselineManifest(ContractModel):
    schema_version: str = "agentlens.baseline.v1"
    baseline_id: UUID
    tenant_id: str
    environment: str
    agent_name: str
    agent_version: str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int = Field(gt=0, le=8192)
    record_count: int = Field(ge=1)
    records_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class Finding(ContractModel):
    finding_id: UUID
    tenant_id: str
    cluster_id: str
    trace_id: str
    score_id: UUID
    severity: FindingSeverity
    root_cause: RootCause
    title: str = Field(min_length=1, max_length=256)
    rationale: list[str]
    state: str = Field(default="open", pattern=r"^(open|acknowledged|resolved)$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
