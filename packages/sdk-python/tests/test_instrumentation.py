"""ADR-008 SDK tests: init, adapters, mapping, span helpers."""

from __future__ import annotations

import pytest
from agentlens import AgentLensConfig, InstrumentationError, agent_run, init, instrument, tool_call
from agentlens.adapters import activate_adk, activate_langchain
from agentlens.mapping import (
    DEFAULT_MAPPING,
    apply_resource_mapping,
    apply_span_mapping,
    load_mapping,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_init_is_preferred_entry_and_instrument_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")

    class _NoopExporter:
        def export(self, spans):  # type: ignore[no-untyped-def]
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
    provider = init(
        framework="generic",
        agent_name="orders",
        agent_version="1.2.3",
        agent_id="orders-agent",
        baseline_ref="11111111-1111-1111-1111-111111111111",
    )
    assert isinstance(provider, TracerProvider)
    resource = provider.resource.attributes
    assert resource["agentlens.agent.id"] == "orders-agent"
    assert resource["agentlens.framework"] == "generic"
    assert resource["agentlens.baseline_ref"] == "11111111-1111-1111-1111-111111111111"

    aliased = instrument(framework="generic", agent_name="orders", agent_version="1.2.3")
    assert isinstance(aliased, TracerProvider)


def test_config_uses_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "orders-agent")
    monkeypatch.setenv("AGENTLENS_BASELINE_REF", "11111111-1111-1111-1111-111111111111")
    config = AgentLensConfig.from_env(
        framework="langgraph",
        agent_name="orders",
        agent_version="1.2.3",
    )
    assert config.otlp_endpoint == "http://collector:4317"
    assert config.service_name == "orders-agent"
    assert config.baseline_ref == "11111111-1111-1111-1111-111111111111"
    assert config.agent_id == "orders"


def test_config_rejects_empty_identity() -> None:
    with pytest.raises(InstrumentationError, match="agent_name"):
        AgentLensConfig.from_env(
            framework="generic",
            agent_name=" ",
            agent_version="1.0.0",
        )


def test_adk_adapter_requires_extra() -> None:
    with pytest.raises(InstrumentationError, match="agentlens\\[adk\\]"):
        activate_adk(TracerProvider())


def test_langchain_adapter_requires_extra() -> None:
    with pytest.raises(InstrumentationError, match="agentlens\\[langchain\\]"):
        activate_langchain(TracerProvider())


def test_tier2_resource_and_span_mapping() -> None:
    mapping = load_mapping()
    assert mapping["version"] == DEFAULT_MAPPING["version"]
    resource = apply_resource_mapping(
        {"service.name": "checkout", "service.version": "9.0.0"},
        mapping,
    )
    assert resource["agentlens.agent.name"] == "checkout"
    assert resource["agentlens.agent.id"] == "checkout"
    assert resource["agentlens.agent.version"] == "9.0.0"
    assert resource["agentlens.framework"] == "generic"

    span = apply_span_mapping(
        {"gen_ai.tool.name": "search", "gen_ai.response.id": "run-1"},
        mapping,
    )
    assert span["tool.name"] == "search"
    assert span["openinference.tool.name"] == "search"
    assert span["agentlens.run.id"] == "run-1"


def test_manual_span_helpers_emit_addendum_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(
        "agentlens.spans._tracer",
        lambda: provider.get_tracer("agentlens"),
    )

    with (
        agent_run(agent_id="orders", run_id="run-123", agent_name="orders") as root,
        tool_call(tool_name="lookup", tool_call_id="call-1", run_id="run-123"),
    ):
        root.set_attribute("agentlens.meta.step", "tool")

    spans = exporter.get_finished_spans()
    assert {span.name for span in spans} == {"agentlens.agent.run", "agentlens.tool.call"}
    by_name = {span.name: span for span in spans}
    assert by_name["agentlens.agent.run"].attributes["agentlens.agent.id"] == "orders"
    assert by_name["agentlens.agent.run"].attributes["agentlens.run.id"] == "run-123"
    assert by_name["agentlens.tool.call"].attributes["tool.name"] == "lookup"
