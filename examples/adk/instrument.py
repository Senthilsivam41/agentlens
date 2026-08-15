from agentlens import init


def configure_observability() -> None:
    init(
        framework="adk",
        agent_name="planner-executor",
        agent_version="2.0.0",
        agent_id="dual-llm-router",
        environment="production",
    )
