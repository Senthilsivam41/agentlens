from agentlens import init


def configure_observability() -> None:
    init(
        framework="langchain",
        agent_name="support-agent",
        agent_version="1.0.0",
        agent_id="support-agent",
        environment="production",
    )
