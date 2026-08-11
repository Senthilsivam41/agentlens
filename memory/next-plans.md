# Next Plans

**Last updated:** 2026-08-11

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

1. Repeat the local recovery harness in the target AKS/EKS environment; the Compose gate is implemented and passed with queue growth, replay, and duplicate-delivery evidence.
2. Run the semantic acceptance harness with an approved embedding-provider credential; the implementation is present, but the credential-backed deterministic score/finding and p95 <60-second gate remain pending.
3. Run tenant-isolation and OIDC acceptance against a real identity provider; run collector mTLS certificate rotation and rejection tests.
4. Run `scripts/pilot_acceptance.py --count 1000 --traces-per-minute 1000` for at least one hour, then a 24-hour soak; tune from measured saturation and latency.
5. Install or provide Helm in the validation environment and rerun generic, AKS, EKS, and platform chart lints; validate Collector configs and every local Markdown link.
6. Deploy edge and platform charts to one AKS or EKS pilot environment; validate outage buffering, replay, backup/restore, rollback, dashboards, and runbooks.
7. Perform security, WCAG 2.2 AA accessibility, and disaster-recovery reviews. Close Phase 8 only when every acceptance artifact is recorded.

## Post-Pilot Candidates

- Canonical orchestration lifecycle semantic contract and AutoClaw file-to-OTLP adapter.
- Framework integration packs for OpenAI Agents SDK, Microsoft Agent Framework/Semantic Kernel, Google ADK, and AutoGen.
- Constrained Text-to-SQL.
- Webhook, Slack, and PagerDuty alerts.
- Human feedback and offline LLM-judge calibration.
- Restricted encrypted raw-content mode.
- Automated baseline candidates.
- Inline cost and retry guardrails.
- Additional agent frameworks.
- HA and multi-region deployment.
