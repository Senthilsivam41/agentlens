"""API configuration."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agentlens_environment: str = "development"
    agentlens_auth_mode: Literal["dev", "oidc"] = "dev"
    agentlens_dev_tenant_id: str = "local"
    agentlens_dev_roles: str = "viewer,analyst,admin"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "agentlens"
    clickhouse_username: str = "agentlens"
    clickhouse_password: SecretStr = SecretStr("")
    oidc_issuer: str = ""
    oidc_audience: str = "agentlens-api"
    oidc_jwks_url: str = ""
    api_query_max_days: int = Field(default=31, ge=1, le=366)
    api_default_page_size: int = Field(default=50, ge=1, le=500)
    api_max_page_size: int = Field(default=200, ge=1, le=1000)
    api_query_timeout_seconds: int = Field(default=10, ge=1, le=60)
    api_max_result_rows: int = Field(default=10_000, ge=100, le=100_000)
    api_rate_limit_per_minute: int = Field(default=600, ge=10, le=100_000)
