from agentlens import init, instrument_utcp_client


def configure_observability(client: object) -> object:
    init(
        framework="generic",
        agent_name="support-agent",
        agent_version="1.0.0",
        tool_protocols=("utcp",),
    )
    return instrument_utcp_client(client)
