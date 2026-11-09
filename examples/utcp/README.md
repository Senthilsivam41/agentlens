# UTCP tool-call adapter (ADR-008)

Tool-protocol add-on, not a framework. It layers onto LangChain, CrewAI, ADK,
LangGraph, or `generic`.

```bash
pip install 'agentlens[utcp]'
```

```python
from agentlens import init, instrument_utcp_client

init(
    framework="langchain",
    agent_name="support-agent",
    agent_version="1.0.0",
    tool_protocols=("utcp",),
)
instrument_utcp_client(client)
```

`tool_protocols=("utcp",)` registers the `agentlens_trace` post-processor type,
including for JSON configs via the `utcp.plugins` entry point.
`instrument_utcp_client` appends that processor to a live client. A client
built from a config that already lists `agentlens_trace` does not get a second
copy.

Each successful `call_tool` emits a child span named `utcp.tool.call` with
`tool.name`, `openinference.span.kind=TOOL`, `agentlens.tool.protocol=utcp`,
the call template's transport, and the manual prefix of the tool name. The
result body is not recorded. String and bytes results record only their length.

The hook is UTCP's `ToolPostProcessor`, which runs only after the protocol call
returns. That leaves four gaps:

- Failed calls (protocol errors, unknown tools, disallowed transports) produce
  no span, so they cannot become `tool_runtime_failure`.
- The span has no start time, so its duration is near zero.
- Tool arguments are not visible to the processor.
- `call_tool_streaming` invokes the processor once per chunk. Put streaming
  tools in `exclude_tools` when that would drown the trace.

```python
{"tool_post_processor_type": "agentlens_trace", "exclude_tools": ["billing.stream"]}
```
