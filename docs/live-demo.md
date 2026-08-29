# Agent Lens — Live Local Demo

One-command setup for a local showcase of ingestion, deterministic scoring, and the investigation dashboard.

For alpha limits (dev auth, API-only baselines), see [alpha-scope.md](alpha-scope.md).

---

## Quick start

### Full demo (semantic drift + findings)

Requires `OPENAI_API_KEY` in `.env`. OpenRouter keys also need:

```bash
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_EMBEDDING_MODEL=openai/text-embedding-3-small
```

```bash
make live-demo
```

This will:

1. Ensure `.env` exists (copy from `.env.example` if missing)
2. Start Compose (`make compose-up`)
3. Wait for API readiness
4. Run semantic acceptance (baseline import → activate → 5 traces → scores → findings)
5. Write [demo-evidence/live-demo-latest.json](demo-evidence/live-demo-latest.json) with browser URLs and talking points

### Structural demo (no embedding key)

```bash
make live-demo-smoke
```

Emits one smoke trace via `scripts/smoke_trace.py`. Scores are **structural_only** — good for showing ingestion and privacy without embeddings.

### Health check only (stack already running)

```bash
make live-demo-check
```

Verifies API, dashboard, and docs respond; refreshes the evidence file with health status.

---

## Script reference

All modes use [scripts/live_demo.py](../scripts/live_demo.py):

```bash
uv run python scripts/live_demo.py --mode full          # same as make live-demo
uv run python scripts/live_demo.py --mode structural   # smoke trace only
uv run python scripts/live_demo.py --mode check         # health only
uv run python scripts/live_demo.py --mode full --skip-compose   # skip compose-up
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--mode` | `full` | `check`, `structural`, or `full` |
| `--skip-compose` | off | Skip `make compose-up` when stack is already up |
| `--api-url` | `http://localhost:18000` | API base URL |
| `--web-url` | `http://localhost:3000` | Dashboard base URL |

---

## After setup

Open the URLs printed by the script, or read them from `docs/demo-evidence/live-demo-latest.json`:

| Tab | URL |
|-----|-----|
| Overview | http://localhost:3000/ |
| Executions | http://localhost:3000/executions |
| Baselines | http://localhost:3000/baselines |
| Execution detail | `walkthrough.dashboard_execution_detail` in evidence JSON |
| API docs | http://localhost:18000/docs |

### Demo B walkthrough (full mode)

1. **Overview** — drift rate, semantic coverage, recent findings
2. **Baselines** — active `semantic-acceptance-agent`, 500 records
3. **Execution detail** — Mahalanobis distance, ambiguity, root cause, rationale
4. **Privacy** — note that prompt/output text is not stored (hashes only)

### Demo A walkthrough (structural mode)

1. Run `make live-demo-smoke` (or re-run `uv run python scripts/smoke_trace.py`)
2. Wait ~20s for trace assembly
3. Open `/executions/<trace_id>` for `pilot-smoke-agent`

---

## Prerequisites

- Docker Desktop (or compatible engine)
- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- `.env` with at least: `CLICKHOUSE_PASSWORD`, `AGENTLENS_HMAC_KEY`, `AGENTLENS_TRANSIENT_KEY`
- For full mode: `OPENAI_API_KEY` (or OpenRouter config above)

```bash
uv sync --all-packages --group dev
make compose-ps    # verify services
curl http://localhost:18000/health/ready
```

---

## Optional add-ons

| Story | Command |
|-------|---------|
| Freshness + privacy gate | `make pilot-acceptance` |
| Outage recovery | `make pilot-recovery` (run before demo; disruptive) |
| SDK instrument example | `examples/langgraph/instrument.py` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dashboard degraded | `make live-demo-check`; `make compose-ps` |
| Trace 404 after smoke | Wait ~20s; retry execution URL |
| Full mode fails on embeddings | Check `OPENAI_API_KEY`; OpenRouter needs `OPENAI_BASE_URL` |
| Semantic timeout | `make live-demo --skip-compose` after stack is warm |
| Invalid evidence JSON | Re-run `make live-demo` or `make live-demo-smoke` |

---

## Related docs

- [README quick start](../README.md)
- [Pilot hardening runbook](pilot-hardening-runbook.md)
- [Alpha scope](alpha-scope.md)
