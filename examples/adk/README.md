# Google ADK 2.0 adapter (ADR-008)

```bash
pip install 'agentlens[adk]'
```

```python
from agentlens import init

init(
    framework="adk",
    agent_name="planner-executor",
    agent_version="2.0.0",
    agent_id="dual-llm-router",
)
```

AgentLens owns the global `TracerProvider` and OTLP export. ADK's built-in
OpenTelemetry instrumentation attaches to that provider. Content capture is
disabled by default (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`) per ADR-005.
