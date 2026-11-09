"""Agent Lens framework-neutral instrumentation helpers."""

from typing import Any

from .errors import InstrumentationError
from .instrumentation import AgentLensConfig, init, instrument
from .spans import agent_run, set_baseline_ref, tool_call


def instrument_utcp_client(client: Any) -> Any:
    """Attach UTCP tool-call tracing to a client. Requires ``agentlens[utcp]``."""
    try:
        from .adapters.utcp import instrument_utcp_client as attach
    except ImportError as exc:
        raise InstrumentationError(
            "utcp instrumentation is unavailable; install agentlens[utcp]"
        ) from exc
    return attach(client)


__all__ = [
    "AgentLensConfig",
    "InstrumentationError",
    "agent_run",
    "init",
    "instrument",
    "instrument_utcp_client",
    "set_baseline_ref",
    "tool_call",
]
