"""FastAPI application factory and versioned HTTP routes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from .auth import Authenticator, CurrentPrincipal
from .config import ApiSettings
from .models import BaselineImportRequest, FindingUpdate, MetricConfigRequest, Page
from .repository import ClickHouseRepository, Repository


def create_app(
    *, settings: ApiSettings | None = None, repository: Repository | None = None
) -> FastAPI:
    selected_settings = settings or ApiSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if repository is None:
            app.state.repository = ClickHouseRepository(selected_settings)
        yield

    app = FastAPI(
        title="Agent Lens API",
        version="0.1.0",
        description="Tenant-scoped agent execution, drift score, finding, and baseline API.",
        lifespan=lifespan,
    )
    app.state.settings = selected_settings
    app.state.authenticator = Authenticator(selected_settings)
    app.state.rate_buckets = defaultdict(lambda: [0, 0])
    if repository is not None:
        app.state.repository = repository

    @app.middleware("http")
    async def security_and_rate_limit(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith("/health/"):
            return cast(Response, await call_next(request))
        authorization = request.headers.get("authorization", "")
        client = request.client.host if request.client else "unknown"
        identity = hashlib.sha256(f"{client}:{authorization}".encode()).hexdigest()
        minute = int(time.time() // 60)
        bucket = request.app.state.rate_buckets[identity]
        if bucket[0] != minute:
            bucket[:] = [minute, 0]
        bucket[1] += 1
        if bucket[1] > selected_settings.api_rate_limit_per_minute:
            return Response(status_code=429, headers={"Retry-After": "60"})
        response = cast(Response, await call_next(request))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def repo(request: Request) -> Repository:
        return cast(Repository, request.app.state.repository)

    async def audit(
        request: Request,
        principal: CurrentPrincipal,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        await repo(request).record_audit(
            tenant_id=principal.tenant_id,
            actor_id=principal.subject,
            actor_roles=sorted(principal.roles),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready(request: Request) -> dict[str, str]:
        if not await repo(request).ready():
            raise HTTPException(status_code=503, detail="storage unavailable")
        return {"status": "ready"}

    @app.get("/v1/executions", response_model=Page, tags=["executions"])
    async def executions(
        request: Request,
        principal: CurrentPrincipal,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        cursor: str | None = None,
        agent_name: str | None = None,
        environment: str | None = None,
        cluster_id: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
    ) -> Page:
        if cursor is not None and not cursor.isdigit():
            raise HTTPException(status_code=422, detail="invalid pagination cursor")
        window_end = started_before or datetime.now(UTC)
        window_start = started_after or window_end - timedelta(
            days=selected_settings.api_query_max_days
        )
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=UTC)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=UTC)
        if window_start >= window_end:
            raise HTTPException(status_code=422, detail="invalid execution time range")
        if window_end - window_start > timedelta(days=selected_settings.api_query_max_days):
            raise HTTPException(status_code=422, detail="execution time range is too large")
        items, next_cursor = await repo(request).list_executions(
            tenant_id=principal.tenant_id,
            limit=limit,
            cursor=cursor,
            filters={
                "agent_name": agent_name,
                "environment": environment,
                "cluster_id": cluster_id,
                "started_after": window_start,
                "started_before": window_end,
            },
        )
        return Page(items=items, next_cursor=next_cursor)

    @app.get("/v1/executions/{trace_id}", tags=["executions"])
    async def execution(
        trace_id: str, request: Request, principal: CurrentPrincipal
    ) -> dict[str, Any]:
        item = await repo(request).execution(tenant_id=principal.tenant_id, trace_id=trace_id)
        if item is None:
            raise HTTPException(status_code=404, detail="execution not found")
        await audit(
            request,
            principal,
            action="execution.read",
            resource_type="execution",
            resource_id=trace_id,
        )
        return item

    @app.get("/v1/executions/{trace_id}/scores", tags=["executions"])
    async def scores(
        trace_id: str, request: Request, principal: CurrentPrincipal
    ) -> list[dict[str, Any]]:
        if await repo(request).execution(tenant_id=principal.tenant_id, trace_id=trace_id) is None:
            raise HTTPException(status_code=404, detail="execution not found")
        return await repo(request).scores(tenant_id=principal.tenant_id, trace_id=trace_id)

    @app.get("/v1/findings", tags=["findings"])
    async def findings(
        request: Request,
        principal: CurrentPrincipal,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> list[dict[str, Any]]:
        return await repo(request).list_findings(tenant_id=principal.tenant_id, limit=limit)

    @app.patch("/v1/findings/{finding_id}", tags=["findings"])
    async def update_finding(
        finding_id: UUID,
        body: FindingUpdate,
        request: Request,
        principal: CurrentPrincipal,
    ) -> dict[str, Any]:
        principal.require("analyst", "admin")
        item = await repo(request).update_finding(
            tenant_id=principal.tenant_id, finding_id=finding_id, state=body.state
        )
        if item is None:
            raise HTTPException(status_code=404, detail="finding not found")
        await audit(
            request,
            principal,
            action="finding.update",
            resource_type="finding",
            resource_id=str(finding_id),
            details={"state": body.state},
        )
        return item

    @app.get("/v1/metrics/summary", tags=["metrics"])
    async def summary(request: Request, principal: CurrentPrincipal) -> dict[str, Any]:
        return await repo(request).summary(tenant_id=principal.tenant_id)

    @app.get("/v1/metrics/timeseries", tags=["metrics"])
    async def timeseries(request: Request, principal: CurrentPrincipal) -> list[dict[str, Any]]:
        return await repo(request).timeseries(tenant_id=principal.tenant_id)

    @app.post(
        "/v1/baseline-imports",
        status_code=status.HTTP_202_ACCEPTED,
        tags=["baselines"],
    )
    async def create_baseline_import(
        body: BaselineImportRequest, request: Request, principal: CurrentPrincipal
    ) -> dict[str, Any]:
        principal.require("admin")
        created = await repo(request).create_baseline_import(
            tenant_id=principal.tenant_id,
            object_uri=body.object_uri,
            checksum=body.checksum,
            actor=principal.subject,
        )
        await audit(
            request,
            principal,
            action="baseline_import.create",
            resource_type="baseline_import",
            resource_id=str(created["import_id"]),
        )
        return created

    @app.get("/v1/baseline-imports/{import_id}", tags=["baselines"])
    async def get_baseline_import(
        import_id: UUID, request: Request, principal: CurrentPrincipal
    ) -> dict[str, Any]:
        item = await repo(request).get_baseline_import(
            tenant_id=principal.tenant_id, import_id=import_id
        )
        if item is None:
            raise HTTPException(status_code=404, detail="baseline import not found")
        return item

    @app.get("/v1/baselines", tags=["baselines"])
    async def baselines(request: Request, principal: CurrentPrincipal) -> list[dict[str, Any]]:
        return await repo(request).list_baselines(tenant_id=principal.tenant_id)

    @app.post("/v1/baselines/{baseline_id}/activate", tags=["baselines"])
    async def activate_baseline(
        baseline_id: UUID, request: Request, principal: CurrentPrincipal
    ) -> dict[str, str]:
        principal.require("admin")
        activated = await repo(request).activate_baseline(
            tenant_id=principal.tenant_id, baseline_id=baseline_id, actor=principal.subject
        )
        if not activated:
            raise HTTPException(status_code=404, detail="baseline not found")
        await audit(
            request,
            principal,
            action="baseline.activate",
            resource_type="baseline",
            resource_id=str(baseline_id),
        )
        return {
            "status": "active",
            "baseline_id": str(baseline_id),
            "baseline_ref": str(baseline_id),
        }

    @app.get("/v1/metric-configs", tags=["configuration"])
    async def metric_configs(request: Request, principal: CurrentPrincipal) -> list[dict[str, Any]]:
        return await repo(request).list_metric_configs(tenant_id=principal.tenant_id)

    @app.post("/v1/metric-configs", status_code=201, tags=["configuration"])
    async def create_metric_config(
        body: MetricConfigRequest, request: Request, principal: CurrentPrincipal
    ) -> dict[str, Any]:
        principal.require("admin")
        created = await repo(request).create_metric_config(
            tenant_id=principal.tenant_id,
            metric_version=body.metric_version,
            config=body.config,
            actor=principal.subject,
        )
        await audit(
            request,
            principal,
            action="metric_config.create",
            resource_type="metric_config",
            resource_id=str(created["config_id"]),
        )
        return created

    @app.get("/v1/events", tags=["events"])
    async def events(request: Request, principal: CurrentPrincipal) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            last_payload = ""
            while not await request.is_disconnected():
                payload = json.dumps(
                    await repo(request).list_findings(tenant_id=principal.tenant_id, limit=10),
                    default=str,
                )
                if payload != last_payload:
                    yield f"event: findings\ndata: {payload}\n\n"
                    last_payload = payload
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(15)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app
