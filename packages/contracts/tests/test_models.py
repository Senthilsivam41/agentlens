from datetime import UTC, datetime, timedelta

import pytest
from agentlens_contracts import Framework, TransientSpan
from pydantic import ValidationError


def make_span(**updates: object) -> TransientSpan:
    started = datetime(2026, 7, 31, tzinfo=UTC)
    values: dict[str, object] = {
        "event_id": "event-0000000001",
        "tenant_id": "tenant-a",
        "cluster_id": "cluster-a",
        "environment": "test",
        "service_name": "example-agent",
        "agent_name": "example-agent",
        "agent_version": "1.0.0",
        "framework": Framework.LANGGRAPH,
        "trace_id": "a" * 32,
        "span_id": "b" * 16,
        "span_name": "agent.run",
        "started_at": started,
        "ended_at": started + timedelta(seconds=1),
    }
    values.update(updates)
    return TransientSpan.model_validate(values)


def test_transient_span_normalizes_time_and_duration() -> None:
    span = make_span()
    assert span.duration_ms == 1000
    assert span.started_at.tzinfo is UTC


def test_transient_span_rejects_invalid_interval() -> None:
    started = datetime(2026, 7, 31, tzinfo=UTC)
    with pytest.raises(ValidationError, match="ended_at"):
        make_span(started_at=started, ended_at=started - timedelta(seconds=1))


def test_secret_text_is_redacted_from_repr() -> None:
    span = make_span(input_text="private prompt")
    assert "private prompt" not in repr(span)
