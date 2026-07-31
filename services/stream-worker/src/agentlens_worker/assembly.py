"""In-memory trace assembly with deterministic deduplication and flush rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from agentlens_contracts import TransientSpan


@dataclass(slots=True)
class TraceState:
    spans: dict[str, TransientSpan] = field(default_factory=dict)
    first_received_at: datetime | None = None
    last_received_at: datetime | None = None
    root_received_at: datetime | None = None

    def ordered_spans(self) -> list[TransientSpan]:
        return sorted(self.spans.values(), key=lambda item: (item.started_at, item.span_id))


class TraceAssembler:
    def __init__(self, *, quiet_period: timedelta, incomplete_timeout: timedelta) -> None:
        self._quiet_period = quiet_period
        self._incomplete_timeout = incomplete_timeout
        self._states: dict[tuple[str, str, str], TraceState] = {}

    def ingest(self, span: TransientSpan, *, received_at: datetime) -> bool:
        key = (span.tenant_id, span.cluster_id, span.trace_id)
        state = self._states.setdefault(key, TraceState())
        is_new = span.span_id not in state.spans
        state.spans[span.span_id] = span
        state.first_received_at = state.first_received_at or received_at
        state.last_received_at = received_at
        if span.parent_span_id is None:
            state.root_received_at = received_at
        return is_new

    def pop_ready(self, *, now: datetime) -> list[list[TransientSpan]]:
        ready: list[list[TransientSpan]] = []
        for key, state in list(self._states.items()):
            if state.last_received_at is None or state.first_received_at is None:
                continue
            root_quiet = (
                state.root_received_at is not None
                and now - state.last_received_at >= self._quiet_period
            )
            expired = now - state.first_received_at >= self._incomplete_timeout
            if root_quiet or expired:
                ready.append(state.ordered_spans())
                del self._states[key]
        return ready

    @property
    def pending_count(self) -> int:
        return len(self._states)
