"""Environment-backed worker configuration."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    worker_mode: Literal["normalize", "assemble", "score"] = "normalize"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_raw_topic: str = "agentlens.otlp.traces.v1"
    kafka_span_topic: str = "agentlens.spans.transient.v1"
    kafka_score_topic: str = "agentlens.executions.score.v1"
    kafka_dlq_topic: str = "agentlens.ingest.dlq.v1"
    kafka_group_id: str = "agentlens-worker"
    agentlens_hmac_key: SecretStr = SecretStr("development-key-must-be-replaced-32")
    agentlens_transient_key: SecretStr = SecretStr("development-transient-key-replace")
    transient_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    trace_quiet_period_seconds: float = Field(default=15, ge=0)
    trace_incomplete_timeout_seconds: float = Field(default=300, ge=1)
    semantic_normal_sample_rate: float = Field(default=0.1, ge=0, le=1)
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "agentlens"
    clickhouse_username: str = "agentlens"
    clickhouse_password: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_embedding_model: str = "text-embedding-3-small"
