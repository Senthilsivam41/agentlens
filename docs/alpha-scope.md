# Alpha scope (honest)

This document states what the **current alpha** is and is not. Prefer this over marketing copy in older drafts.

## Operator model

| Dimension | Alpha reality |
|-----------|----------------|
| Auth | Default `AGENTLENS_AUTH_MODE=dev` — single-operator, trusted-network. No login required locally. |
| OIDC | Implemented in the API (`AGENTLENS_AUTH_MODE=oidc` + issuer/JWKS) but **not** the documented local default and **not** proven against a live IdP for Phase 8. |
| Tenancy | Dev tenant comes from `AGENTLENS_DEV_TENANT_ID`. Cross-tenant denial is coded; live multi-tenant proof is a Phase 8 gate. |
| Network | Local Docker Compose. Production charts exist; live AKS/EKS acceptance is still open. |

## Baseline governance UI

| Surface | Alpha reality |
|---------|----------------|
| `GET /v1/baselines` | Supported; dashboard `/baselines` **lists** imported versions. |
| `POST /v1/baseline-imports` | Supported (admin); **no** dashboard form. |
| `POST /v1/baselines/{id}/activate` | Supported (admin); **no** dashboard button. |
| `agentlens.baseline_ref` | Client/SDK attribute; equals imported `baseline_id` UUID. |

**Alpha baseline ops are API-driven.** Use curl/OpenAPI or the semantic acceptance harness.

## What “drift detection” requires

Structural scoring works without an embedding provider. **Semantic** Mahalanobis / ambiguity scoring and findings need:

1. An imported + activated baseline package.
2. An embedding credential (`OPENAI_API_KEY` for the default model) on the score worker.
3. A passing `make pilot-semantic-acceptance` run (Phase 8 gate).

Until that gate is recorded, do not claim production-ready semantic drift for external pilots.

## Deferred (not alpha)

- Text-to-SQL / NL query over ClickHouse
- Webhooks, Slack, PagerDuty
- CLI (`agentlens trace tail`, `agentlens drift check`)
- **LlamaIndex adapter** — backlog only; **not** alpha-blocking. Pull forward only if a named pilot requires it. Alpha ships LangGraph / LangChain / CrewAI / ADK via `agentlens.init()`.
- HA / multi-region

See [ADR-008](adr/008-developer-integration-instrumentation.md) (instrumentation) and [next plans](../memory/next-plans.md) (Phase 8).
