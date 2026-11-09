"""UTCP post-processor adapter tests."""

from __future__ import annotations

import builtins
from typing import Any

import pytest

pytest.importorskip("utcp")

from agentlens import InstrumentationError, agent_run, init, instrument_utcp_client
from agentlens.adapters.utcp import AgentLensTracePostProcessor, register
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from utcp.data.call_template import CallTemplate
from utcp.data.tool import Tool
from utcp.data.utcp_client_config import UtcpClientConfigSerializer
from utcp.interfaces.tool_post_processor import ToolPostProcessorConfigSerializer


def _noop_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoopExporter:
        def export(self, spans: object) -> int:
            del spans
            return 0

        def shutdown(self, timeout_millis: int = 30000) -> None:
            del timeout_millis

        def force_flush(self, timeout_millis: int = 30000) -> bool:
            del timeout_millis
            return True

    monkeypatch.setattr(
        "agentlens.instrumentation.OTLPSpanExporter",
        lambda **kwargs: _NoopExporter(),
    )


def _capture(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    def tracer() -> object:
        return provider.get_tracer("agentlens")

    monkeypatch.setattr("agentlens.spans._tracer", tracer)
    monkeypatch.setattr("agentlens.adapters.utcp._tracer", tracer)
    return exporter


def _tool(name: str = "billing.refund") -> tuple[Any, Any]:
    template = CallTemplate(name="billing-http", call_template_type="http")
    return Tool(name=name, tool_call_template=template), template


def test_span_is_a_child_and_omits_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    tool, template = _tool()
    exporter = _capture(monkeypatch)
    secret = "secret-refund-body-42"
    returned = None
    with agent_run(agent_id="orders", run_id="run-1", agent_name="orders"):
        returned = AgentLensTracePostProcessor().post_process(None, tool, template, secret)

    assert returned == secret
    spans = {span.name: span for span in exporter.get_finished_spans()}
    tool_span = spans["utcp.tool.call"]
    root = spans["agentlens.agent.run"]
    assert tool_span.parent is not None
    assert tool_span.parent.span_id == root.context.span_id
    attributes = dict(tool_span.attributes or {})
    assert attributes["tool.name"] == "billing.refund"
    assert attributes["openinference.tool.name"] == "billing.refund"
    assert attributes["openinference.span.kind"] == "TOOL"
    assert attributes["agentlens.tool.protocol"] == "utcp"
    assert attributes["agentlens.tool.transport"] == "http"
    assert attributes["agentlens.tool.manual"] == "billing"
    assert attributes["agentlens.tool.result_type"] == "str"
    assert attributes["agentlens.tool.result_size"] == len(secret)
    assert all(secret not in str(value) for value in attributes.values())


def test_non_text_result_records_type_only(monkeypatch: pytest.MonkeyPatch) -> None:
    tool, template = _tool()
    exporter = _capture(monkeypatch)
    secret = "secret-refund-body-42"
    AgentLensTracePostProcessor().post_process(None, tool, template, {"body": secret})
    attributes = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attributes["agentlens.tool.result_type"] == "dict"
    assert "agentlens.tool.result_size" not in attributes
    assert secret not in str(attributes)


def test_filters_suppress_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    tool, template = _tool()
    exporter = _capture(monkeypatch)
    suppressed = [
        AgentLensTracePostProcessor(exclude_tools=["billing.refund"]),
        AgentLensTracePostProcessor(only_include_tools=["other.tool"]),
        AgentLensTracePostProcessor(exclude_manuals=["billing"]),
        AgentLensTracePostProcessor(only_include_manuals=["shipping"]),
    ]
    for processor in suppressed:
        exporter.clear()
        assert processor.post_process(None, tool, template, "ok") == "ok"
        assert not exporter.get_finished_spans()

    exporter.clear()
    AgentLensTracePostProcessor(only_include_manuals=["billing"]).post_process(
        None, tool, template, "ok"
    )
    assert [span.name for span in exporter.get_finished_spans()] == ["utcp.tool.call"]


def test_tracing_errors_do_not_break_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Boom:
        def start_as_current_span(self, *_args: object, **_kwargs: object) -> object:
            raise RuntimeError("tracer down")

    monkeypatch.setattr("agentlens.adapters.utcp._tracer", lambda: _Boom())
    tool, template = _tool()
    assert AgentLensTracePostProcessor().post_process(None, tool, template, "ok") == "ok"


def test_config_round_trip_and_repeat_register() -> None:
    assert register() is True
    assert register() is True
    assert "agentlens_trace" in (
        ToolPostProcessorConfigSerializer.tool_post_processor_implementations
    )
    serializer = UtcpClientConfigSerializer()
    config = serializer.validate_dict(
        {
            "post_processing": [
                {
                    "tool_post_processor_type": "agentlens_trace",
                    "exclude_tools": ["billing.refund"],
                }
            ]
        }
    )
    processor = config.post_processing[0]
    assert processor.tool_post_processor_type == "agentlens_trace"
    assert processor.exclude_tools == ["billing.refund"]
    dumped = serializer.to_dict(config)
    assert dumped["post_processing"][0]["tool_post_processor_type"] == "agentlens_trace"
    assert dumped["post_processing"][0]["exclude_tools"] == ["billing.refund"]


def test_instrument_utcp_client_is_idempotent() -> None:
    class _Config:
        def __init__(self) -> None:
            self.post_processing: list[object] = []

    class _Client:
        def __init__(self) -> None:
            self.config = _Config()

    client = _Client()
    assert instrument_utcp_client(client) is client
    assert instrument_utcp_client(client) is client
    assert len(client.config.post_processing) == 1
    processor = client.config.post_processing[0]
    assert getattr(processor, "tool_post_processor_type", None) == "agentlens_trace"


def test_init_layers_utcp_without_changing_framework(monkeypatch: pytest.MonkeyPatch) -> None:
    _noop_exporter(monkeypatch)
    provider = init(
        framework="generic",
        agent_name="orders",
        agent_version="1.0.0",
        tool_protocols=("utcp",),
    )
    assert isinstance(provider, TracerProvider)
    assert provider.resource.attributes["agentlens.framework"] == "generic"
    assert "agentlens_trace" in (
        ToolPostProcessorConfigSerializer.tool_post_processor_implementations
    )


def test_init_rejects_an_unknown_tool_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    _noop_exporter(monkeypatch)
    with pytest.raises(InstrumentationError, match="unsupported tool protocol"):
        init(
            framework="generic",
            agent_name="orders",
            agent_version="1.0.0",
            tool_protocols=("nope",),  # type: ignore[arg-type]
        )


def test_init_reports_a_missing_utcp_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    _noop_exporter(monkeypatch)
    real_import = builtins.__import__

    def guarded(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "utcp" or name.startswith("utcp."):
            raise ImportError("no utcp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(InstrumentationError, match=r"agentlens\[utcp\]"):
        init(
            framework="generic",
            agent_name="orders",
            agent_version="1.0.0",
            tool_protocols=("utcp",),
        )


def test_public_helper_reports_a_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "agentlens.adapters.utcp", None)
    client = type("Client", (), {})()
    with pytest.raises(InstrumentationError, match=r"agentlens\[utcp\]"):
        instrument_utcp_client(client)
