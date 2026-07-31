# Next Plans

**Last updated:** 2026-08-01

Only the current phase may move to `in-progress`. A phase becomes `complete` after its gate passes.

## Phase Sequence

| Order | Phase | Status | Dependency | Completion gate |
| --- | --- | --- | --- | --- |
| 1 | Phase 0 — Repository foundation | `complete` | None | Python/Node workspaces, pinned locks, CI, Dockerfiles, Compose, ADRs, lint, type, and test commands exist and have run. |
| 2 | Phase 1 — Contracts and ClickHouse schema | `complete` | Phase 0 | Versioned contracts and tenant-scoped migrations exist; smoke telemetry reconstructs without durable raw text. |
| 3 | Phase 2 — Python SDK and AKS/EKS edge collector | `complete` | Phase 1 contracts | Optional LangGraph/CrewAI SDK and generic AKS/EKS-compatible edge Helm chart are implemented. |
| 4 | Phase 3 — Shared secure ingestion | `complete` | Phase 2 | Edge/platform collectors, mTLS configuration, identity overwrite, redaction, disk queueing, and replay-oriented Kafka ingestion are implemented and configs validate. |
| 5 | Phase 4 — Streaming and trace assembly | `complete` | Phase 3 | Live smoke spans produced one complete logical execution and structural score through Redpanda and ClickHouse. |
| 6 | Phase 5 — Imported baselines and scoring | `complete` | Phase 4 | Baseline validation/fitting, versioned storage, Mahalanobis/ambiguity/volatility scoring, sampling, encryption, and deterministic tests are implemented. |
| 7 | Phase 6 — API, OIDC, tenant isolation | `complete` | Phase 5 schemas | Tenant-scoped API, OIDC JWT validation, RBAC, audit, limits, and isolation tests are implemented; local ClickHouse API queries pass. |
| 8 | Phase 7 — Dashboard and deployments | `complete` | Phase 6 OpenAPI | Dashboard, Compose, platform/edge Helm charts, health checks, and container builds are implemented and previously validated. |
| 9 | Phase 8 — Pilot hardening | `in-progress` | Phases 0–7 | Security, privacy, recovery, load, freshness, accessibility, and live AKS/EKS gates pass. |
| 10 | Post-pilot expansion | `not-started` | Successful pilot | Individually approved Text-to-SQL, alerts, feedback, and guardrails ship. |

## Immediate Next Work: Phase 8

1. Restore dependencies with `CI=true pnpm install --frozen-lockfile`, then rerun lint, typecheck, Vitest, and the Next.js production build.
2. Run the full repository validation set: Python checks, Compose render, Collector config validation, both Helm lints, image builds, `git diff --check`, and local Markdown-link verification.
3. Add automated end-to-end coverage for the proven OTLP-to-API smoke path, including Kafka `earliest` recovery and concurrent dashboard API requests.
4. Exercise an imported fixed baseline with an embedding-provider test credential; prove deterministic semantic score and finding creation under the 60-second p95 target.
5. Run privacy tests proving durable prompt/output values are HMAC hashes and encrypted transient records expire within 15 minutes.
6. Run tenant-isolation and OIDC acceptance against a real identity provider; run collector mTLS certificate rotation and rejection tests.
7. Execute load and soak tests at 1,000 traces/minute, then tune worker replicas, Kafka partitions, ClickHouse batching, and API limits from evidence.
8. Deploy edge and platform charts to one AKS or EKS pilot environment; validate outage buffering, replay, backup/restore, rollback, dashboards, and runbooks.
9. Perform security, accessibility, and disaster-recovery reviews. Close Phase 8 only when every acceptance artifact is recorded.

## Post-Pilot Candidates

- Constrained Text-to-SQL.
- Webhook, Slack, and PagerDuty alerts.
- Human feedback and offline LLM-judge calibration.
- Restricted encrypted raw-content mode.
- Automated baseline candidates.
- Inline cost and retry guardrails.
- Additional agent frameworks.
- HA and multi-region deployment.
