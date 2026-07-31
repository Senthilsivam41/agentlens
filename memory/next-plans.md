# Next Plans

**Last updated:** 2026-07-31

Only the current phase may move to `in-progress`. A phase becomes `complete` after its gate passes.

## Phase Sequence

| Order | Phase | Status | Dependency | Completion gate |
| --- | --- | --- | --- | --- |
| 1 | Phase 0 — Repository foundation | `not-started` | None | Fresh clone builds, tests, and validates Compose. |
| 2 | Phase 1 — Contracts and ClickHouse schema | `not-started` | Phase 0 | Fixtures migrate and reconstruct without durable raw text. |
| 3 | Phase 2 — Python SDK and AKS/EKS edge collector | `not-started` | Phase 1 contracts | LangGraph sends equivalent telemetry through SDK or plain OTLP. |
| 4 | Phase 3 — Shared secure ingestion | `not-started` | Phase 2 | mTLS identity, redaction, buffering, and replay pass integration tests. |
| 5 | Phase 4 — Streaming and trace assembly | `not-started` | Phase 3 | Replayed spans produce one logical execution and full structural coverage. |
| 6 | Phase 5 — Imported baselines and scoring | `not-started` | Phase 4 | Fixed corpus produces deterministic, versioned scores. |
| 7 | Phase 6 — API, OIDC, tenant isolation | `not-started` | Phase 5 schemas | Authenticated finding-to-execution flow works without tenant leakage. |
| 8 | Phase 7 — Dashboard and deployments | `not-started` | Phase 6 OpenAPI | Compose and Kubernetes flows work for LangGraph and CrewAI. |
| 9 | Phase 8 — Pilot hardening | `not-started` | Phases 0–7 | Security, privacy, recovery, load, freshness, and accessibility gates pass. |
| 10 | Post-pilot expansion | `not-started` | Successful pilot | Individually approved Text-to-SQL, alerts, feedback, and guardrails ship. |

## Immediate Next Work: Phase 0

1. Establish monorepo directories for API, web, worker, contracts, migrations, infrastructure, examples, and tests.
2. Bootstrap pinned Python and Node toolchains.
3. Add formatting, linting, type checking, unit-test commands, and CI.
4. Produce a truthful, health-checkable Compose foundation.
5. Convert locked architecture decisions into ADRs.
6. Pass the Phase 0 completion gate before starting Phase 1.

## Post-Pilot Candidates

- Constrained Text-to-SQL.
- Webhook, Slack, and PagerDuty alerts.
- Human feedback and offline LLM-judge calibration.
- Restricted encrypted raw-content mode.
- Automated baseline candidates.
- Inline cost and retry guardrails.
- Additional agent frameworks.
- HA and multi-region deployment.

