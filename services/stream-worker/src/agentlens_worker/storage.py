"""ClickHouse persistence. All methods accept durable, text-free contracts."""

from __future__ import annotations

import json
from typing import Any

import clickhouse_connect
from agentlens_contracts import (
    BaselineManifest,
    DurableSpan,
    ExecutionFeatures,
    ExecutionScore,
    Finding,
)

from .baseline import BaselineArtifact
from .config import WorkerSettings


class ClickHouseStorage:
    def __init__(self, settings: WorkerSettings) -> None:
        self._client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_username,
            password=settings.clickhouse_password.get_secret_value(),
            database=settings.clickhouse_database,
        )

    def ping(self) -> bool:
        return bool(self._client.ping())

    def insert_spans(self, spans: list[DurableSpan]) -> None:
        if not spans:
            return
        columns = list(type(spans[0]).model_fields)
        rows = [[_encode(getattr(span, column)) for column in columns] for span in spans]
        self._client.insert("spans", rows, column_names=columns)

    def upsert_execution(self, features: ExecutionFeatures) -> None:
        payload = features.model_dump(mode="python")
        payload["tool_retry_counts_json"] = json.dumps(payload.pop("tool_retry_counts"))
        columns = list(payload)
        self._client.insert(
            "executions", [[_encode(payload[column]) for column in columns]], column_names=columns
        )

    def insert_score(self, score: ExecutionScore) -> None:
        payload = score.model_dump(mode="python")
        sampling = payload.pop("sampling")
        payload["sampling_policy"] = sampling["policy_version"]
        payload["sampling_reason"] = sampling["reason"]
        columns = list(payload)
        self._client.insert(
            "execution_scores",
            [[_encode(payload[column]) for column in columns]],
            column_names=columns,
        )

    def insert_finding(self, finding: Finding) -> None:
        payload = finding.model_dump(mode="python")
        columns = list(payload)
        self._client.insert(
            "findings", [[_encode(payload[column]) for column in columns]], column_names=columns
        )

    def insert_baseline(self, manifest: BaselineManifest, artifact: BaselineArtifact) -> None:
        payload = {
            "baseline_id": manifest.baseline_id,
            "tenant_id": manifest.tenant_id,
            "environment": manifest.environment,
            "agent_name": manifest.agent_name,
            "agent_version": manifest.agent_version,
            "status": "candidate",
            "embedding_provider": manifest.embedding_provider,
            "embedding_model": manifest.embedding_model,
            "embedding_dimensions": manifest.embedding_dimensions,
            "record_count": manifest.record_count,
            "feature_dimension": len(artifact.mean_vector),
            "mean_vector": artifact.mean_vector,
            "inverse_covariance": artifact.inverse_covariance,
            "pca_mean": artifact.pca_mean,
            "pca_components": artifact.pca_components,
            "intent_centroids_json": json.dumps(artifact.intent_centroids),
            "thresholds_json": json.dumps(
                {
                    "drift_threshold": artifact.drift_threshold,
                    "ambiguity_threshold": artifact.ambiguity_threshold,
                    "ambiguity_alpha": artifact.ambiguity_alpha,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "manifest_json": manifest.model_dump_json(),
            "artifact_json": artifact.to_json(),
            "created_at": manifest.created_at,
            "activated_at": None,
            "retired_at": None,
        }
        columns = list(payload)
        self._client.insert(
            "baseline_versions",
            [[_encode(payload[column]) for column in columns]],
            column_names=columns,
        )

    def list_pending_baseline_imports(self, *, limit: int = 10) -> list[dict[str, Any]]:
        result = self._client.query(
            """
            SELECT import_id, tenant_id, object_uri, checksum, status, validation_errors,
                   created_by, created_at, updated_at, baseline_id
            FROM baseline_imports FINAL
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %(limit)s
            """,
            parameters={"limit": limit},
        )
        return [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]

    def update_baseline_import(self, row: dict[str, Any]) -> None:
        payload = {
            "import_id": row["import_id"],
            "tenant_id": row["tenant_id"],
            "object_uri": row["object_uri"],
            "checksum": row["checksum"],
            "status": row["status"],
            "validation_errors": row.get("validation_errors") or [],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "baseline_id": row.get("baseline_id"),
        }
        columns = list(payload)
        self._client.insert(
            "baseline_imports",
            [[_encode(payload[column]) for column in columns]],
            column_names=columns,
        )

    def active_baseline(
        self, *, tenant_id: str, environment: str, agent_name: str, agent_version: str
    ) -> BaselineArtifact | None:
        result = self._client.query(
            """
            SELECT artifact_json
            FROM baseline_versions FINAL
            WHERE tenant_id = %(tenant_id)s
              AND environment = %(environment)s
              AND agent_name = %(agent_name)s
              AND agent_version = %(agent_version)s
              AND status = 'active'
            ORDER BY activated_at DESC
            LIMIT 1
            """,
            parameters={
                "tenant_id": tenant_id,
                "environment": environment,
                "agent_name": agent_name,
                "agent_version": agent_version,
            },
        )
        if not result.result_rows:
            return None
        return BaselineArtifact.from_json(str(result.result_rows[0][0]))


def _encode(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value
