"""Manual span helpers for the SDK fallback path (ADR-008 Tier 3)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.util.types import AttributeValue

from . import attributes as attrs


def _tracer() -> trace.Tracer:
    return trace.get_tracer("agentlens")


@contextmanager
def agent_run(
    *,
    agent_id: str,
    run_id: str | None = None,
    agent_name: str | None = None,
    extra_attributes: dict[str, AttributeValue] | None = None,
) -> Iterator[Span]:
    """Start an AgentLens agent-run span with required addendum attributes."""
    resolved_run_id = run_id or str(uuid4())
    span_attrs: dict[str, AttributeValue] = {
        attrs.AGENT_ID: agent_id,
        attrs.RUN_ID: resolved_run_id,
    }
    if agent_name:
        span_attrs[attrs.AGENT_NAME] = agent_name
    if extra_attributes:
        span_attrs.update(extra_attributes)
    with _tracer().start_as_current_span("agentlens.agent.run", attributes=span_attrs) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def tool_call(
    *,
    tool_name: str,
    tool_call_id: str | None = None,
    run_id: str | None = None,
    extra_attributes: dict[str, AttributeValue] | None = None,
) -> Iterator[Span]:
    """Start a tool-call span using OpenInference-compatible tool attributes."""
    span_attrs: dict[str, AttributeValue] = {
        attrs.TOOL_NAME: tool_name,
        attrs.OPENINFERENCE_TOOL_NAME: tool_name,
    }
    if tool_call_id:
        span_attrs[attrs.TOOL_CALL_ID] = tool_call_id
    if run_id:
        span_attrs[attrs.RUN_ID] = run_id
    if extra_attributes:
        span_attrs.update(extra_attributes)
    with _tracer().start_as_current_span("agentlens.tool.call", attributes=span_attrs) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def set_baseline_ref(span: Span, baseline_ref: str) -> None:
    span.set_attribute(attrs.BASELINE_REF, baseline_ref)


def set_run_metadata(span: Span, **metadata: Any) -> None:
    for key, value in metadata.items():
        if value is None:
            continue
        span.set_attribute(f"agentlens.meta.{key}", value)
