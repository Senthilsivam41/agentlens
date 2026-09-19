"""Tenant-scoped data repositories."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import clickhouse_connect

from .config import ApiSettings


def _with_baseline_ref(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    baseline_id = enriched.get("baseline_id")
    if baseline_id is not None:
        enriched["baseline_ref"] = str(baseline_id)
    elif "baseline_ref" not in enriched:
        enriched["baseline_ref"] = None
    return enriched


class Repository(Protocol):
    async def ready(self) -> bool: ...

    async def list_executions(
        self, *, tenant_id: str, limit: int, cursor: str | None, filters: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str | None]: ...

    async def execution(self, *, tenant_id: str, trace_id: str) -> dict[str, Any] | None: ...

    async def scores(self, *, tenant_id: str, trace_id: str) -> list[dict[str, Any]]: ...

    async def list_findings(self, *, tenant_id: str, limit: int) -> list[dict[str, Any]]: ...

    async def update_finding(
        self, *, tenant_id: str, finding_id: UUID, state: str
    ) -> dict[str, Any] | None: ...

    async def summary(self, *, tenant_id: str) -> dict[str, Any]: ...

    async def timeseries(self, *, tenant_id: str) -> list[dict[str, Any]]: ...

    async def create_baseline_import(
        self, *, tenant_id: str, object_uri: str, checksum: str, actor: str
    ) -> dict[str, Any]: ...

    async def get_baseline_import(
        self, *, tenant_id: str, import_id: UUID
    ) -> dict[str, Any] | None: ...

    async def list_baselines(self, *, tenant_id: str) -> list[dict[str, Any]]: ...

    async def activate_baseline(self, *, tenant_id: str, baseline_id: UUID, actor: str) -> bool: ...

    async def list_metric_configs(self, *, tenant_id: str) -> list[dict[str, Any]]: ...

    async def create_metric_config(
        self, *, tenant_id: str, metric_version: str, config: dict[str, Any], actor: str
    ) -> dict[str, Any]: ...

    async def record_audit(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        actor_roles: list[str],
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None: ...


class MemoryRepository:
    """Test/dev repository preserving tenant boundaries."""

    def __init__(self) -> None:
        self.executions: list[dict[str, Any]] = []
        self.execution_scores: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.baselines: list[dict[str, Any]] = []
        self.baseline_imports: list[dict[str, Any]] = []
        self.metric_configs: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []

    async def ready(self) -> bool:
        return True

    async def list_executions(
        self, *, tenant_id: str, limit: int, cursor: str | None, filters: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str | None]:
        del filters
        scoped = [item for item in self.executions if item["tenant_id"] == tenant_id]
        start = int(cursor or 0)
        items = scoped[start : start + limit]
        next_cursor = str(start + limit) if start + limit < len(scoped) else None
        return items, next_cursor

    async def execution(self, *, tenant_id: str, trace_id: str) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.executions
                if item["tenant_id"] == tenant_id and item["trace_id"] == trace_id
            ),
            None,
        )

    async def scores(self, *, tenant_id: str, trace_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self.execution_scores
            if item["tenant_id"] == tenant_id and item["trace_id"] == trace_id
        ]

    async def list_findings(self, *, tenant_id: str, limit: int) -> list[dict[str, Any]]:
        return [item for item in self.findings if item["tenant_id"] == tenant_id][:limit]

    async def update_finding(
        self, *, tenant_id: str, finding_id: UUID, state: str
    ) -> dict[str, Any] | None:
        for item in self.findings:
            if item["tenant_id"] == tenant_id and str(item["finding_id"]) == str(finding_id):
                item["state"] = state
                item["updated_at"] = datetime.now(UTC)
                return item
        return None

    async def summary(self, *, tenant_id: str) -> dict[str, Any]:
        executions = [item for item in self.executions if item["tenant_id"] == tenant_id]
        scores = [item for item in self.execution_scores if item["tenant_id"] == tenant_id]
        semantic = [item for item in scores if item.get("mahalanobis_distance") is not None]
        return {
            "executions": len(executions),
            "drifted": sum(bool(item.get("is_drifted")) for item in scores),
            "semantic_scored": len(semantic),
            "semantic_coverage": len(semantic) / len(executions) if executions else 0,
            "open_findings": sum(
                item["tenant_id"] == tenant_id and item.get("state") == "open"
                for item in self.findings
            ),
        }

    async def timeseries(self, *, tenant_id: str) -> list[dict[str, Any]]:
        del tenant_id
        return []

    async def create_baseline_import(
        self, *, tenant_id: str, object_uri: str, checksum: str, actor: str
    ) -> dict[str, Any]:
        record = {
            "import_id": uuid4(),
            "tenant_id": tenant_id,
            "object_uri": object_uri,
            "checksum": checksum,
            "status": "pending",
            "validation_errors": [],
            "baseline_id": None,
            "baseline_ref": None,
            "created_by": actor,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        self.baseline_imports.append(record)
        return _with_baseline_ref(record)

    async def get_baseline_import(
        self, *, tenant_id: str, import_id: UUID
    ) -> dict[str, Any] | None:
        for item in self.baseline_imports:
            if item["tenant_id"] == tenant_id and str(item["import_id"]) == str(import_id):
                return _with_baseline_ref(item)
        return None

    async def list_baselines(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [
            _with_baseline_ref(item) for item in self.baselines if item["tenant_id"] == tenant_id
        ]

    async def activate_baseline(self, *, tenant_id: str, baseline_id: UUID, actor: str) -> bool:
        del actor
        selected = next(
            (
                item
                for item in self.baselines
                if item["tenant_id"] == tenant_id and str(item["baseline_id"]) == str(baseline_id)
            ),
            None,
        )
        if selected is None:
            return False
        for item in self.baselines:
            if item["tenant_id"] != tenant_id:
                continue
            same_segment = (
                item.get("environment") == selected.get("environment")
                and item.get("agent_name") == selected.get("agent_name")
                and item.get("agent_version") == selected.get("agent_version")
            )
            if not same_segment:
                continue
            item["status"] = "active" if str(item["baseline_id"]) == str(baseline_id) else "retired"
        return True

    async def list_metric_configs(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return [item for item in self.metric_configs if item["tenant_id"] == tenant_id]

    async def create_metric_config(
        self, *, tenant_id: str, metric_version: str, config: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        record = {
            "config_id": uuid4(),
            "tenant_id": tenant_id,
            "metric_version": metric_version,
            "status": "candidate",
            "config": config,
            "created_by": actor,
            "created_at": datetime.now(UTC),
        }
        self.metric_configs.append(record)
        return record

    async def record_audit(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        actor_roles: list[str],
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.audit_events.append(
            {
                "audit_id": uuid4(),
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "actor_roles": actor_roles,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "occurred_at": datetime.now(UTC),
            }
        )


class ClickHouseRepository:
    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
        self._client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_username,
            password=settings.clickhouse_password.get_secret_value(),
            database=settings.clickhouse_database,
        )
        # clickhouse-connect reuses one HTTP session and rejects overlapping
        # operations on it. Serialize access while keeping blocking I/O off the
        # event loop; API replicas provide horizontal query concurrency.
        self._operation_lock = asyncio.Lock()

    async def ready(self) -> bool:
        async with self._operation_lock:
            return bool(await asyncio.to_thread(self._client.ping))

    async def _query(
        self, sql: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self._operation_lock:
            result = await asyncio.to_thread(
                self._client.query,
                sql,
                parameters=parameters or {},
                settings={
                    "max_execution_time": self._settings.api_query_timeout_seconds,
                    "max_result_rows": self._settings.api_max_result_rows,
                    "result_overflow_mode": "throw",
                },
            )
        return [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]

    async def _insert(self, table: str, row: dict[str, Any]) -> None:
        columns = list(row)
        async with self._operation_lock:
            await asyncio.to_thread(
                self._client.insert,
                table,
                [[row[column] for column in columns]],
                column_names=columns,
            )

    async def list_executions(
        self, *, tenant_id: str, limit: int, cursor: str | None, filters: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str | None]:
        offset = max(0, int(cursor or 0))
        conditions = ["tenant_id = %(tenant_id)s"]
        parameters: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit + 1, "offset": offset}
        for name in ("agent_name", "environment", "cluster_id"):
            if filters.get(name):
                conditions.append(f"{name} = %({name})s")
                parameters[name] = filters[name]
        if filters.get("started_after"):
            conditions.append("started_at >= %(started_after)s")
            parameters["started_after"] = filters["started_after"]
        if filters.get("started_before"):
            conditions.append("started_at < %(started_before)s")
            parameters["started_before"] = filters["started_before"]
        rows = await self._query(
            f"""
            SELECT * FROM executions FINAL
            WHERE {" AND ".join(conditions)}
            ORDER BY started_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            parameters,
        )
        has_more = len(rows) > limit
        return rows[:limit], str(offset + limit) if has_more else None

    async def execution(self, *, tenant_id: str, trace_id: str) -> dict[str, Any] | None:
        rows = await self._query(
            """SELECT * FROM executions FINAL
            WHERE tenant_id=%(tenant_id)s AND trace_id=%(trace_id)s LIMIT 1""",
            {"tenant_id": tenant_id, "trace_id": trace_id},
        )
        return rows[0] if rows else None

    async def scores(self, *, tenant_id: str, trace_id: str) -> list[dict[str, Any]]:
        return await self._query(
            """SELECT * FROM execution_scores FINAL
            WHERE tenant_id=%(tenant_id)s AND trace_id=%(trace_id)s ORDER BY computed_at DESC""",
            {"tenant_id": tenant_id, "trace_id": trace_id},
        )

    async def list_findings(self, *, tenant_id: str, limit: int) -> list[dict[str, Any]]:
        return await self._query(
            """SELECT * FROM findings FINAL WHERE tenant_id=%(tenant_id)s
            ORDER BY created_at DESC LIMIT %(limit)s""",
            {"tenant_id": tenant_id, "limit": limit},
        )

    async def update_finding(
        self, *, tenant_id: str, finding_id: UUID, state: str
    ) -> dict[str, Any] | None:
        rows = await self._query(
            """SELECT * FROM findings FINAL
            WHERE tenant_id=%(tenant_id)s AND finding_id=%(finding_id)s LIMIT 1""",
            {"tenant_id": tenant_id, "finding_id": finding_id},
        )
        if not rows:
            return None
        row = rows[0]
        row["state"] = state
        row["updated_at"] = datetime.now(UTC)
        await self._insert("findings", row)
        return row

    async def summary(self, *, tenant_id: str) -> dict[str, Any]:
        execution_rows, score_rows, finding_rows = await asyncio.gather(
            self._query(
                """SELECT countDistinct(trace_id) AS executions FROM executions FINAL
                WHERE tenant_id=%(tenant_id)s""",
                {"tenant_id": tenant_id},
            ),
            self._query(
                """SELECT countIf(current.2 = true) AS drifted,
                          countIf(current.1 IS NOT NULL) AS semantic_scored
                FROM (
                  SELECT trace_id,
                         argMax(tuple(mahalanobis_distance, is_drifted), computed_at) AS current
                  FROM execution_scores FINAL
                  WHERE tenant_id=%(tenant_id)s
                  GROUP BY trace_id
                )""",
                {"tenant_id": tenant_id},
            ),
            self._query(
                """SELECT count() AS open_findings FROM findings FINAL
                WHERE tenant_id=%(tenant_id)s AND state='open'""",
                {"tenant_id": tenant_id},
            ),
        )
        executions = int(execution_rows[0]["executions"])
        semantic_scored = int(score_rows[0]["semantic_scored"])
        return {
            "executions": executions,
            "drifted": int(score_rows[0]["drifted"]),
            "semantic_scored": semantic_scored,
            "semantic_coverage": semantic_scored / executions if executions else 0,
            "open_findings": int(finding_rows[0]["open_findings"]),
        }

    async def timeseries(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return await self._query(
            """
            SELECT toStartOfHour(e.started_at) AS timestamp,
                   countDistinct(e.trace_id) AS executions,
                   countIf(s.is_drifted=true) AS drifted,
                   countIf(s.mahalanobis_distance IS NOT NULL) AS semantic_scored,
                   avgOrDefault(e.trajectory_volatility) AS average_volatility
            FROM executions e FINAL
            LEFT JOIN (
              SELECT tenant_id, trace_id,
                     argMax(is_drifted, computed_at) AS is_drifted,
                     argMax(mahalanobis_distance, computed_at) AS mahalanobis_distance
              FROM execution_scores FINAL
              GROUP BY tenant_id, trace_id
            ) s ON e.tenant_id=s.tenant_id AND e.trace_id=s.trace_id
            WHERE e.tenant_id=%(tenant_id)s
            GROUP BY timestamp ORDER BY timestamp
            """,
            {"tenant_id": tenant_id},
        )

    async def create_baseline_import(
        self, *, tenant_id: str, object_uri: str, checksum: str, actor: str
    ) -> dict[str, Any]:
        record = {
            "import_id": uuid4(),
            "tenant_id": tenant_id,
            "object_uri": object_uri,
            "checksum": checksum,
            "status": "pending",
            "validation_errors": [],
            "baseline_id": None,
            "created_by": actor,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await self._insert("baseline_imports", record)
        return _with_baseline_ref(record)

    async def get_baseline_import(
        self, *, tenant_id: str, import_id: UUID
    ) -> dict[str, Any] | None:
        rows = await self._query(
            """SELECT * FROM baseline_imports FINAL
            WHERE tenant_id=%(tenant_id)s AND import_id=%(import_id)s LIMIT 1""",
            {"tenant_id": tenant_id, "import_id": import_id},
        )
        return _with_baseline_ref(rows[0]) if rows else None

    async def list_baselines(self, *, tenant_id: str) -> list[dict[str, Any]]:
        rows = await self._query(
            """SELECT * FROM baseline_versions FINAL
            WHERE tenant_id=%(tenant_id)s ORDER BY created_at DESC""",
            {"tenant_id": tenant_id},
        )
        return [_with_baseline_ref(row) for row in rows]

    async def activate_baseline(self, *, tenant_id: str, baseline_id: UUID, actor: str) -> bool:
        rows = await self._query(
            """SELECT * FROM baseline_versions FINAL
            WHERE tenant_id=%(tenant_id)s AND baseline_id=%(baseline_id)s LIMIT 1""",
            {"tenant_id": tenant_id, "baseline_id": baseline_id},
        )
        if not rows:
            return False
        selected = rows[0]
        segment = await self._query(
            """SELECT * FROM baseline_versions FINAL
            WHERE tenant_id=%(tenant_id)s
              AND environment=%(environment)s
              AND agent_name=%(agent_name)s
              AND agent_version=%(agent_version)s
              AND status='active'""",
            {
                "tenant_id": tenant_id,
                "environment": selected["environment"],
                "agent_name": selected["agent_name"],
                "agent_version": selected["agent_version"],
            },
        )
        now = datetime.now(UTC)
        version = int(now.timestamp() * 1_000_000)
        changed: list[dict[str, Any]] = []
        for active in segment:
            if str(active["baseline_id"]) == str(baseline_id):
                continue
            active["status"] = "retired"
            active["retired_at"] = now
            active["version"] = version
            changed.append(active)
        selected["status"] = "active"
        selected["activated_at"] = now
        selected["retired_at"] = None
        selected["version"] = version + 1
        changed.append(selected)
        for row in changed:
            await self._insert("baseline_versions", row)
        del actor
        return True

    async def list_metric_configs(self, *, tenant_id: str) -> list[dict[str, Any]]:
        return await self._query(
            """SELECT * FROM metric_configs FINAL
            WHERE tenant_id=%(tenant_id)s ORDER BY created_at DESC""",
            {"tenant_id": tenant_id},
        )

    async def create_metric_config(
        self, *, tenant_id: str, metric_version: str, config: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        record = {
            "config_id": uuid4(),
            "tenant_id": tenant_id,
            "metric_version": metric_version,
            "status": "candidate",
            "config_json": json.dumps(config, separators=(",", ":"), sort_keys=True),
            "created_by": actor,
            "created_at": datetime.now(UTC),
            "activated_at": None,
        }
        await self._insert("metric_configs", record)
        return record

    async def record_audit(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        actor_roles: list[str],
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "audit_id": uuid4(),
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_roles": actor_roles,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details_json": json.dumps(details or {}, separators=(",", ":"), sort_keys=True),
            "occurred_at": datetime.now(UTC),
        }
        await self._insert("audit_events", record)
