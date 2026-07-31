from agentlens import instrument


def configure_observability() -> None:
    instrument(
        framework="langgraph",
        agent_name="research-agent",
        agent_version="1.0.0",
        environment="production",
    )
