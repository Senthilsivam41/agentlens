# Agent Lens — Agentic AI Mathematical Drift Observability

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Enabled-blue.svg)](https://opentelemetry.io/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-OLAP-brightgreen.svg)](https://clickhouse.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)

Open-source observability for agent workflows (**LangGraph**, **LangChain**, **CrewAI**, **Google ADK**). Agent Lens measures behavioral drift, tool-loop volatility, and prompt ambiguity with deterministic vector math on OpenTelemetry traces — **without LLM-as-a-judge on the scoring path**.

> **Alpha status (honest scope):** local Compose / single-operator pilot. Default auth is `AGENTLENS_AUTH_MODE=dev` (trusted network). Dashboard baselines page is **read-only**; import and activate baselines via the API. Live AKS/EKS, real OIDC, and load/soak evidence are still Phase 8 gates — see [pilot hardening runbook](docs/pilot-hardening-runbook.md) and [alpha scope](docs/alpha-scope.md).

## Docs

- [Architecture](docs/agentlens-architecture.md)
- [Development roadmap](docs/agentlens-development-roadmap.md)
- [ADRs](docs/adr/README.md)
- [OpenInference attribute addendum](docs/openinference-attribute-addendum.md)
- [Edge collector identity (ADR-004)](docs/edge-collector-identity.md)
- [Alpha scope (auth / UI / ops)](docs/alpha-scope.md)
- [Phase 8 pilot hardening runbook](docs/pilot-hardening-runbook.md)
- [Product positioning](docs/product-positioning-and-ecosystem-integration.md)
- [Deploy on Render](docs/deploy-render.md)

## Project memory

- [Memory index](memory/README.md)
- [Current status](memory/current-status.md)
- [Next plans](memory/next-plans.md)
- [Completed actions](memory/completed-actions.md)
- [Locked decisions](memory/decisions.md)

---

## Features (what ships in alpha)

- **Deterministic drift signals:** Mahalanobis distance ($D_M$), context ambiguity ($H_{\text{amb}}$), trajectory volatility ($V_{\text{traj}}$) computed asynchronously off the request path.
- **Root-cause oriented findings:** Separates prompt ambiguity from agent/tool failure modes when a baseline is active.
- **OTLP + OpenInference contract:** Edge/platform collectors, redaction, hash-only durable content (ADR-005), Kafka/Redpanda streaming workers.
- **Imported baseline governance:** Externally curated packages → validate → candidate → activate (ADR-006); client tag `agentlens.baseline_ref`.
- **Instrumentation front door (ADR-008):** `agentlens.init()` plus thin adapters for LangGraph, LangChain, CrewAI, and ADK; Tier-2 config-driven attribute mapping for plain OTLP.
- **Investigation API + dashboard:** Executions, scores, findings, metrics summary; baselines listed in the UI.

### Explicitly not in alpha

- Natural-language / Text-to-SQL querying (post-pilot).
- Webhook / Slack / PagerDuty alerting (ADR-009 candidate).
- Multi-tenant OIDC as the default local mode (code exists; use `AGENTLENS_AUTH_MODE=oidc` only after configuring issuer/JWKS).
- Dashboard controls to import or activate baselines (API-only today).

---

## Architecture (alpha path)

```text
[ Agent + agentlens.init() / OTLP ]
            │ OTLP (edge collector)
            ▼
[ Platform collector + identity gateway ]
            │ Kafka / Redpanda
            ▼
[ Normalize → assemble → score workers ] → ClickHouse
            │
            ▼
[ FastAPI :18000 ] ←→ [ Next.js dashboard :3000 ]
```
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/99186c8a-9fd1-490f-b7e1-a5f23089f028" />


- **Ingestion:** OpenTelemetry Collector Contrib + OpenInference semantics.
- **Store:** ClickHouse (production path); DuckDB is offline/analysis only.
- **Workers:** Python stream workers (normalize, assemble, score, baseline import).
- **API:** FastAPI, tenant-scoped routes, RBAC hooks.
- **UI:** Next.js investigation views.

---

## Quick start (local Compose)

### Prerequisites

- Docker Desktop (or compatible engine)
- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- Optional: `OPENAI_API_KEY` only if you want **semantic** scoring acceptance (embeddings). Structural path and smoke traces work without it.

### 1. Clone and configure

```bash
git clone https://github.com/Senthilsivam41/agentlens.git
cd agentlens
cp .env.example .env
# Edit .env: set CLICKHOUSE_PASSWORD, AGENTLENS_HMAC_KEY, AGENTLENS_TRANSIENT_KEY.
# Leave AGENTLENS_AUTH_MODE=dev for local alpha.
```

### 2. Start the stack

```bash
make compose-up
# or: docker compose --env-file .env -f infra/compose/docker-compose.yaml up -d --build
```

### 3. Smoke-check

| Service | Endpoint | Expected |
| --- | --- | --- |
| API ready | `http://localhost:18000/health/ready` | `{"status":"ready"}` |
| API docs | `http://localhost:18000/docs` | OpenAPI |
| Dashboard | `http://localhost:3000` | Overview |
| ClickHouse | `http://localhost:8123/ping` | `Ok.` |

### 4. Instrument an agent

```bash
pip install 'agentlens[langgraph]'   # or [langchain], [crewai], [adk]
```

```python
from agentlens import init

init(
    framework="langgraph",  # langchain | crewai | adk | generic
    agent_name="research-agent",
    agent_version="1.0.0",
    otlp_endpoint="http://localhost:4317",
    insecure=True,
)
```

See `examples/langgraph`, `examples/langchain`, `examples/crewai`, and `examples/adk`.

### 5. Baseline ops (API-driven in alpha)

```bash
# Create import (admin) → worker validates → activate candidate
curl -s -X POST http://localhost:18000/v1/baseline-imports \
  -H 'content-type: application/json' \
  -d '{"object_uri":"https://…/package.zip","checksum":"<sha256>"}'

curl -s -X POST "http://localhost:18000/v1/baselines/<baseline_id>/activate"
```

The dashboard `/baselines` page lists versions only; it does not import or activate.

### 6. Acceptance harnesses

```bash
make pilot-acceptance          # freshness, concurrency, durable privacy
make pilot-recovery            # edge/broker outage replay
OPENAI_API_KEY=… make pilot-semantic-acceptance   # import → activate → score → finding
```

---

## Mathematical reference

### Trajectory distance ($D_M$)

$$D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu}_g)^T \boldsymbol{\Sigma}_g^{-1} (\mathbf{x} - \boldsymbol{\mu}_g)}$$

### Context ambiguity ($H_{\text{amb}}$)

$$H_{\text{amb}}(Q) = -\sum_{i=1}^{N} P(x_i) \log_2 P(x_i) + \alpha \cdot \left(1 - \frac{1}{m}\sum_{j=1}^{m} \cos(\mathbf{q}, \mathbf{c}_j)\right)$$

### Trajectory volatility ($V_{\text{traj}}$)

$$V_{\text{traj}} = w_s \cdot \left(\frac{N_{\text{steps}}}{\bar{N}}\right)^2 + w_t \cdot \left(\frac{T_{\text{used}}}{\bar{T}}\right) + w_r \cdot \sum_{i=1}^{M} R_i^2$$

---

## License

MIT. See `LICENSE`.
