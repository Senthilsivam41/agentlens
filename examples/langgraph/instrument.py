from agentlens import init


def configure_observability() -> None:
    init(
        framework="langgraph",
        agent_name="research-agent",
        agent_version="1.0.0",
        environment="production",
    )
