from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agentlens_api import create_app
from agentlens_api.config import ApiSettings
from agentlens_api.repository import MemoryRepository
from fastapi.testclient import TestClient


def client_and_repository() -> tuple[TestClient, MemoryRepository]:
    repository = MemoryRepository()
    settings = ApiSettings(
        agentlens_auth_mode="dev",
        agentlens_dev_tenant_id="tenant-a",
        agentlens_dev_roles="viewer,analyst,admin",
    )
    return TestClient(create_app(settings=settings, repository=repository)), repository


def test_health_and_ready() -> None:
    client, _ = client_and_repository()
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_execution_queries_never_return_other_tenant() -> None:
    client, repository = client_and_repository()
    repository.executions.extend(
        [
            {"tenant_id": "tenant-a", "trace_id": "a" * 32},
            {"tenant_id": "tenant-b", "trace_id": "b" * 32},
        ]
    )
    response = client.get("/v1/executions")
    assert response.status_code == 200
    assert [item["trace_id"] for item in response.json()["items"]] == ["a" * 32]
    assert client.get(f"/v1/executions/{'b' * 32}").status_code == 404
    assert client.get(f"/v1/executions/{'a' * 32}").status_code == 200
    assert repository.audit_events[-1]["action"] == "execution.read"


def test_admin_can_create_baseline_import() -> None:
    client, _ = client_and_repository()
    response = client.post(
        "/v1/baseline-imports",
        json={"object_uri": "s3://baselines/package", "checksum": "a" * 64},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_finding_update_is_tenant_scoped() -> None:
    client, repository = client_and_repository()
    finding_id = uuid4()
    repository.findings.append(
        {
            "finding_id": finding_id,
            "tenant_id": "tenant-b",
            "state": "open",
        }
    )
    response = client.patch(f"/v1/findings/{finding_id}", json={"state": "acknowledged"})
    assert response.status_code == 404


def test_execution_query_rejects_invalid_cursor_and_unbounded_window() -> None:
    client, _ = client_and_repository()
    assert client.get("/v1/executions?cursor=invalid").status_code == 422
    end = datetime(2026, 7, 31, tzinfo=UTC)
    start = end - timedelta(days=32)
    response = client.get(
        "/v1/executions",
        params={"started_after": start.isoformat(), "started_before": end.isoformat()},
    )
    assert response.status_code == 422


def test_rate_limit_returns_retry_after() -> None:
    repository = MemoryRepository()
    settings = ApiSettings(
        agentlens_auth_mode="dev",
        agentlens_dev_tenant_id="tenant-a",
        api_rate_limit_per_minute=10,
    )
    client = TestClient(create_app(settings=settings, repository=repository))
    for _ in range(10):
        assert client.get("/v1/metrics/summary").status_code == 200
    limited = client.get("/v1/metrics/summary")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_dashboard_queries_are_safe_under_concurrency() -> None:
    client, repository = client_and_repository()
    repository.executions.extend(
        {"tenant_id": "tenant-a", "trace_id": f"{index:032x}"} for index in range(20)
    )

    paths = ["/v1/metrics/summary", "/v1/executions?limit=20"] * 20
    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(client.get, paths))

    assert all(response.status_code == 200 for response in responses)
    summaries = [
        response.json()
        for response, path in zip(responses, paths, strict=True)
        if "summary" in path
    ]
    assert all(summary["executions"] == 20 for summary in summaries)
