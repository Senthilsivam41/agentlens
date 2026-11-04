# Drift demo

A simulated customer-support agent that sends labeled traffic into Agent Lens. Prompts are seeded and sometimes vague, so a walkthrough can show each root-cause classification without calling a chat model.

Every trace and the imported baseline use:

| Field | Value |
| --- | --- |
| Agent | `demo-support-agent` |
| Version | `1.0.0` |
| Environment | `demo` |

The executions list and the baselines table both show those columns, and demo rows carry a **Demo** badge. The filtered walkthrough page is:

`http://localhost:3000/executions?agent_name=demo-support-agent&environment=demo`

## What each scenario is built to score

| Scenario | What the agent does | Expected root cause |
| --- | --- | --- |
| `clear` | Specified prompt, canonical tool path, stable answer | `compliant` |
| `vague_rambling` | Long, underspecified prompt, unknown tools, off-topic answer | `user_prompt_ambiguity` |
| `vague_clarify_loop` | Short prompt (`fix it`) and a repeated tool path | `high_volatility` |
| `tool_failure` | Vague account reference, tool span errors | `tool_runtime_failure` |
| `agent_regression` | Clear prompt, but the wrong tools and another intent's answer | `agent_logic_failure` |

`clear` and `vague_rambling` are only scored semantically when `SEMANTIC_NORMAL_SAMPLE_RATE=1`. The default of `0.1` skips most of them. `make demo-drift` sets the rate to `1` and recreates the score worker.

## Run it

From the repository root, with the Compose `.env` in place and `OPENAI_API_KEY` set (embeddings only; the agent itself is simulated):

```bash
make demo-drift
```

Or, if the stack is already up with `SEMANTIC_NORMAL_SAMPLE_RATE=1`:

```bash
PYTHONPATH=examples/drift-demo uv run python -m drift_demo bootstrap
PYTHONPATH=examples/drift-demo uv run python -m drift_demo traffic --count 60 --vague-ratio 0.4 --seed 7
PYTHONPATH=examples/drift-demo uv run python -m drift_demo report
```

`python -m drift_demo all` runs the three steps. Traffic is reproducible for a given `--seed`. `--regression-ratio` is applied first; `--vague-ratio` applies to the remaining traces.

Without `OPENAI_API_KEY`, `traffic` still sends traces. Only the loop and tool-failure scenarios produce findings. The report says when other scores are `embedding_unavailable`.

## Where to click

1. Open the walkthrough URL printed by the report.
2. Confirm the banner says this is demo traffic, and that each row is badged **Demo** with environment `demo`.
3. Read the action flag. **Red** means act on the agent or a tool. **Orange** means review the prompt or the path. **Green** means no action. The same colors are on Mahalanobis distance, input ambiguity, and trajectory volatility.
4. On **Imported baselines**, the `demo-support-agent` row is the population those scores were compared with.
