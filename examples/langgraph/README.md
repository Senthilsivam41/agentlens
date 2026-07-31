# LangGraph Integration Example

Install the optional adapter and point it at the in-cluster edge collector:

```bash
pip install 'agentlens[langgraph]' langgraph
export OTEL_EXPORTER_OTLP_ENDPOINT=http://agentlens-edge.observability.svc:4317
```

Initialize before constructing or invoking the graph:

```python
from agentlens import instrument

instrument(
    framework="langgraph",
    agent_name="research-agent",
    agent_version="1.0.0",
    environment="production",
)
```

Applications already emitting OpenInference-compatible OTLP need only change their OTLP endpoint.

