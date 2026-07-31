"""Typed API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(ApiModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


class FindingUpdate(ApiModel):
    state: Literal["acknowledged", "resolved"]


class BaselineImportRequest(ApiModel):
    object_uri: str = Field(pattern=r"^(s3|https?)://")
    checksum: str = Field(pattern=r"^[0-9a-f]{64}$")


class BaselineImportResponse(ApiModel):
    import_id: UUID
    status: str


class MetricConfigRequest(ApiModel):
    metric_version: str = Field(min_length=1, max_length=64)
    config: dict[str, Any]


class TimeseriesPoint(ApiModel):
    timestamp: datetime
    executions: int
    drifted: int
    semantic_scored: int
    average_volatility: float
