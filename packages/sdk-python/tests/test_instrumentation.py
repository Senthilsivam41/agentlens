import pytest
from agentlens import AgentLensConfig, InstrumentationError


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


def test_config_rejects_empty_identity() -> None:
    with pytest.raises(InstrumentationError, match="agent_name"):
        AgentLensConfig.from_env(
            framework="generic",
            agent_name=" ",
            agent_version="1.0.0",
        )
