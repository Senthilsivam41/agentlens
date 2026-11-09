"""UTCP tool-call tracing via the official ToolPostProcessor hook (ADR-008).

UTCP runs post-processors only after a protocol call returns. This adapter
therefore traces successful calls. It does not see failures, arguments, or a
start time, and streaming calls invoke it once per chunk. Those limits are
recorded in ADR-008.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, cast

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from utcp.data.call_template import CallTemplate
from utcp.data.tool import Tool
from utcp.exceptions import UtcpSerializerValidationError
from utcp.interfaces.serializer import Serializer
from utcp.interfaces.tool_post_processor import (
    ToolPostProcessor,
    ToolPostProcessorConfigSerializer,
)
from utcp.plugins.discovery import register_tool_post_processor

from .. import attributes as attrs
from ..errors import InstrumentationError

logger = logging.getLogger(__name__)

_PROCESSOR_TYPE: Literal["agentlens_trace"] = "agentlens_trace"


def _tracer() -> trace.Tracer:
    return trace.get_tracer("agentlens")


def _manual_name(tool: Tool, call_template: CallTemplate) -> str:
    prefix, separator, _rest = str(tool.name).partition(".")
    if separator:
        return prefix
    return str(call_template.name)


class AgentLensTracePostProcessor(ToolPostProcessor):  # type: ignore[misc]
    """Emit one OpenInference TOOL span for a successful UTCP tool result.

    Filters match UTCP's ``LimitStringsPostProcessor``. Manual filters also
    match the manual prefix of ``tool.name`` (``billing`` in ``billing.refund``),
    because ``call_tool`` passes the tool call template rather than the manual.
    An empty include list does not restrict, matching the upstream processor.
    """

    tool_post_processor_type: Literal["agentlens_trace"] = _PROCESSOR_TYPE
    exclude_tools: list[str] | None = None
    only_include_tools: list[str] | None = None
    exclude_manuals: list[str] | None = None
    only_include_manuals: list[str] | None = None

    def post_process(
        self,
        caller: Any,
        tool: Tool,
        manual_call_template: CallTemplate,
        result: Any,
    ) -> Any:
        del caller
        try:
            if self._selected(tool, manual_call_template):
                self._emit(tool, manual_call_template, result)
        except Exception:
            logger.exception("agentlens utcp trace post-processor failed")
        return result

    def _selected(self, tool: Tool, call_template: CallTemplate) -> bool:
        tool_name = str(tool.name)
        manuals = {_manual_name(tool, call_template), str(call_template.name)}
        if self.exclude_tools and tool_name in self.exclude_tools:
            return False
        if self.only_include_tools and tool_name not in self.only_include_tools:
            return False
        if self.exclude_manuals and manuals.intersection(self.exclude_manuals):
            return False
        if not self.only_include_manuals:
            return True
        return bool(manuals.intersection(self.only_include_manuals))

    def _emit(self, tool: Tool, call_template: CallTemplate, result: Any) -> None:
        tool_name = str(tool.name)
        span_attrs: dict[str, str | int] = {
            attrs.TOOL_NAME: tool_name,
            attrs.OPENINFERENCE_TOOL_NAME: tool_name,
            attrs.OPENINFERENCE_SPAN_KIND: "TOOL",
            attrs.TOOL_PROTOCOL: "utcp",
            attrs.TOOL_TRANSPORT: str(call_template.call_template_type),
            attrs.TOOL_MANUAL: _manual_name(tool, call_template),
            attrs.TOOL_RESULT_TYPE: type(result).__name__,
        }
        if isinstance(result, str | bytes):
            span_attrs[attrs.TOOL_RESULT_SIZE] = len(result)
        with _tracer().start_as_current_span("utcp.tool.call", attributes=span_attrs):
            return None


class AgentLensTracePostProcessorConfigSerializer(
    Serializer[AgentLensTracePostProcessor]  # type: ignore[misc]
):
    """Serializer registered for ``tool_post_processor_type=agentlens_trace``."""

    def to_dict(self, obj: AgentLensTracePostProcessor) -> dict[str, Any]:
        return cast(dict[str, Any], obj.model_dump())

    def validate_dict(self, data: dict[str, Any]) -> AgentLensTracePostProcessor:
        try:
            return cast(
                AgentLensTracePostProcessor,
                AgentLensTracePostProcessor.model_validate(data),
            )
        except Exception as exc:
            raise UtcpSerializerValidationError(
                "Invalid AgentLensTracePostProcessor"
            ) from exc


def register() -> bool:
    """Register the processor type. Repeat calls with ``override=False`` are safe.

    Returns true when this call inserts the type or a re-entrant plugin load
    already did. UTCP loads ``utcp.plugins`` entry points from ``Serializer``
    construction, and that entry point calls ``register`` again.
    """
    added = register_tool_post_processor(
        _PROCESSOR_TYPE,
        AgentLensTracePostProcessorConfigSerializer(),
        override=False,
    )
    implementations = ToolPostProcessorConfigSerializer.tool_post_processor_implementations
    return added or _PROCESSOR_TYPE in implementations


def instrument_utcp_client(client: Any) -> Any:
    """Append the trace processor to a client unless one is already configured."""
    register()
    processors = client.config.post_processing
    already = any(
        getattr(item, "tool_post_processor_type", None) == _PROCESSOR_TYPE for item in processors
    )
    if already:
        return client
    processors.append(AgentLensTracePostProcessor())
    return client


def activate_utcp(provider: TracerProvider) -> None:
    """Register the UTCP processor type against an already-installed provider."""
    del provider
    try:
        import utcp  # noqa: F401
    except ImportError as exc:
        raise InstrumentationError(
            "utcp instrumentation is unavailable; install agentlens[utcp]"
        ) from exc
    register()
