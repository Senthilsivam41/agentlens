from agentlens import instrument


def configure_observability() -> None:
    instrument(
        framework="crewai",
        agent_name="support-crew",
        agent_version="1.0.0",
        environment="production",
    )
