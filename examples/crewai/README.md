# CrewAI Integration Example

Install the optional adapter:

```bash
pip install 'agentlens[crewai]' crewai
```

Configure before starting a crew:

```python
from agentlens import instrument

instrument(
    framework="crewai",
    agent_name="support-crew",
    agent_version="1.0.0",
    environment="production",
)
```

