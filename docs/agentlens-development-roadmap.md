# Agent Lens — Development Roadmap and Task List

**Status:** implementation roadmap (historical checklist plus current status)
**Planning rule:** complete each phase’s acceptance checks before broadening scope.

## Current repository assessment

The repository is a runnable local alpha/pilot implementation. Phases 0–7
(foundation, contracts, SDK/edge, secure ingestion, streaming, scoring, API,
dashboard, and deployments) are complete at pilot scope. Phase 8 pilot
hardening is in progress; credential-backed semantic acceptance, live
AKS/EKS/OIDC/mTLS evidence, load/soak, accessibility, and disaster-recovery
gates remain open. The current status table below is authoritative; the
checkboxes in the original phase task lists are retained as historical task
provenance and must not be read as runtime evidence.

| Current phase | Status | Evidence / gate |
| --- | --- | --- |
| Phases 0–7 | `complete` at pilot scope | Implemented source, Compose/Helm, tests, and local pipeline evidence |
| Phase 8 — Pilot hardening | `in-progress` | [Pilot hardening runbook](pilot-hardening-runbook.md) |
| Post-pilot expansion | `not-started` | Text-to-SQL, alerts, feedback, guardrails, and additional framework packs |

## Phase 0 — Establish the delivery foundation (complete at pilot scope)

- [x] Rename the product consistently to **Agent Lens** while preserving `agent-drift-dashboard` as a legacy architecture identifier.
- [x] Choose the implemented monorepo layout: `apps/api`, `apps/web`, `services/stream-worker`, `infra`, `packages/contracts`, `examples`.
- [x] Add language/tool manifests, `.env.example`, formatting/linting, tests, CI, and a local development Makefile/task runner.
- [x] Pin Docker images and Python/Node dependencies.
- [x] Add an architecture decision record directory and move decisions into individual ADRs.

**Exit criteria:** a fresh clone can run formatting, unit tests, and a no-op compose validation without undisclosed local state.

## Phase 1 — Define data contracts and schema migrations (complete at pilot scope)

- [x] Write OpenTelemetry/OpenInference attribute mapping and required/optional-field policy.
- [x] Add `tenant_id`, environment, agent/version, model/provider, trace/span identifiers, and data-quality flags to the schema.
- [x] Create migration-managed ClickHouse tables for durable spans, executions, scores, baselines, findings, stream jobs, and audit events.
- [x] Add partitioning, ordering, TTL, and codecs based on target query patterns.
- [x] Version schemas and metric configurations; create representative span/trace fixtures.
- [x] Verify the OTLP → Kafka → worker → ClickHouse mapping against the pinned collector and worker builds.

**Exit criteria:** fixtures ingest successfully and can be queried as complete executions; migrations are repeatable on an empty database.

## Phase 2 — Make ingestion safe and observable (complete at pilot scope; hardening remains)

- [x] Configure collector health, memory limiter, batching, retry queue, backpressure, and diagnostic metrics.
- [x] Implement secret/PII redaction and hash-only durable storage before ClickHouse persistence.
- [x] Add sample LangGraph and CrewAI instrumented applications.
- [x] Add end-to-end tests: emit OTLP → collector → Kafka → workers → ClickHouse → execution rollup.
- [ ] Measure and report dropped spans, rejected payloads, explicit payload-size violations, and ingestion lag (Phase 8 hardening).

**Exit criteria:** a sample agent produces an inspectable, redacted execution; an intentional secret never reaches the raw-span table.

## Phase 3 — Build deterministic analytics (implemented as streaming workers)

- [x] Implement trace feature extraction: ordered tool path, step count, retries, tokens, duration, and error/timeout signals. Cost inputs remain post-pilot.
- [x] Implement embedding adapter with explicit model/dimension/version metadata and deterministic test fixtures.
- [x] Implement baseline creation, minimum cohort checks, covariance regularization, and baseline approval metadata.
- [x] Implement `D_M`, `H_amb`, and `V_traj` with unit tests using known numerical fixtures.
- [x] Persist component values, threshold configuration, metric version, classification, and “insufficient evidence” reasons.
- [x] Add idempotent normalize/assemble/score stream workers plus audit/logging and replay support.
- [x] Validate signal quality with deterministic structural and semantic acceptance harnesses; provider-backed precision/recall remains a Phase 8 gate.

**Exit criteria:** a fixed fixture corpus produces deterministic, versioned metrics; reruns do not duplicate or alter results unexpectedly.

## Phase 4 — Deliver the investigation API (complete at pilot scope)

- [x] Implement health/readiness, execution list/detail, metric trend, findings, baseline, and configuration endpoints.
- [x] Publish OpenAPI and use shared request-response contracts.
- [x] Add pagination, bounded date ranges, query timeout limits, structured error responses, and rate limits.
- [x] Add authentication and tenant/role authorization.
- [x] Add audit events for baseline/configuration updates and sensitive trace access.

**Exit criteria:** an authenticated user can get from a finding to a single trace and score breakdown through documented APIs only.

## Phase 5 — Build the Agent Lens dashboard (pilot scope)

- [x] Create an executive overview: drift rate, volatility trend, data coverage, top affected agents, and recent findings.
- [x] Create an investigation view: trace timeline, path comparison, score components, classification rationale, and baseline metadata.
- [x] Create the read-only baseline listing and API-driven baseline lifecycle with role restrictions.
- [ ] Add client-side “what-if” controls clearly marked as simulations (post-pilot).
- [ ] Add empty/loading/error states and accessibility checks (Phase 8 hardening).

**Exit criteria:** a product owner can navigate trend → finding → execution and understand why the system made its classification.

## Phase 6 — Hardening and operations (Phase 8 continuation)

- [ ] Add RBAC, audit logs, encryption/secret management, retention tests, and tenant-isolation tests.
- [ ] Define deployment profiles for local Docker, staging, and production Kubernetes/managed ClickHouse.
- [ ] Add load tests for target spans/sec, dashboard query concurrency, and analytics windows.
- [ ] Instrument Agent Lens itself with traces, metrics, logs, and SLO dashboards (Phase 8).
- [ ] Create backup/restore, incident response, data deletion, and upgrade runbooks (Phase 8/post-pilot).

**Exit criteria:** staging meets agreed throughput, privacy, recovery, and observability requirements.

## Deferred capabilities (post-pilot; not current alpha)

- [ ] Constrained natural-language analytics using a read-only semantic layer; never directly execute unvalidated model SQL.
- [ ] Alert rules, Slack/PagerDuty/webhooks, issue tracker integrations.
- [ ] Inline circuit breakers for severe retry/cost patterns.
- [ ] Human feedback workflows and optional offline LLM-as-a-judge calibration.
- [ ] Additional frameworks, distributed deployment, and cross-project benchmarking.

## Recommended implementation order

`contracts → migrations → safe ingestion → trace rollups → deterministic scores → API → investigation UI → auth/operations → optional AI query features`

This ordering proves the data and scoring loop before investing in dashboard polish or LLM-assisted querying.

## Initial issue breakdown

| Priority | Issue | Dependency |
| --- | --- | --- |
| P0 | Bootstrap monorepo/tooling and pinned local stack | None |
| P0 | ClickHouse migrations plus trace fixture corpus | Bootstrap |
| P0 | Validate collector/exporter integration and redact pipeline | Migrations |
| P0 | Sample instrumented agent and E2E ingest test | Collector |
| P0 | Trace rollup and volatility scoring worker | Fixture corpus |
| P1 | Baseline lifecycle and Mahalanobis/ambiguity scoring | Rollups + embeddings |
| P1 | Typed API for traces, metrics, and findings | Metrics tables |
| P1 | Investigation dashboard | Typed API |
| P1 | Auth, tenant isolation, and audit trail | API |
| P2 | Executive dashboard and alerting | Findings API |
| P2 | Constrained text-to-SQL | Auth + semantic layer |

## Definition of done for every issue

- Contract/schema change documented and versioned.
- Automated tests cover success, invalid input, and tenant/privacy boundary where relevant.
- Observability added for the new runtime path.
- Migration/rollback and configuration behavior documented.
- User-facing behavior verified in the local compose environment.
