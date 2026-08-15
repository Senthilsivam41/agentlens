# LangChain adapter (ADR-008)

```bash
pip install 'agentlens[langchain]'
```

```python
from agentlens import init

init(
    framework="langchain",
    agent_name="support-agent",
    agent_version="1.0.0",
)
```

Uses OpenInference `LangChainInstrumentor` under the hood and stamps AgentLens
resource attributes (`agentlens.agent.*`, `agentlens.framework`, optional
`agentlens.baseline_ref`).
