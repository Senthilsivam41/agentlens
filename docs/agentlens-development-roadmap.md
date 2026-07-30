# Agent Lens — Development Roadmap and Task List

**Status:** implementation backlog  
**Planning rule:** complete each phase’s acceptance checks before broadening scope.

## Current repository assessment

The repository contains valuable drafts: a README, architecture notes, a Docker Compose outline, an OTel collector configuration, a partial ClickHouse schema, and an empty backend placeholder. It does **not** yet contain a functional backend/frontend, worker, test suite, dependency manifests, or verified collector-to-ClickHouse pipeline. Treat infrastructure files as design inputs to validate, not as an executable MVP.

## Phase 0 — Establish the delivery foundation

- [ ] Rename the product consistently to **Agent Lens** while preserving `agent-drift-dashboard` only where it is an intentional package/deployment identifier.
- [ ] Choose monorepo layout: `apps/api`, `apps/web`, `workers/analytics`, `infra`, `packages/contracts`, `examples`.
- [ ] Add language/tool manifests, `.env.example`, formatting/linting, tests, CI, and a local development Makefile/task runner.
- [ ] Pin Docker images and Python/Node dependencies; remove `latest` tags from reproducible environments.
- [ ] Add an architecture decision record directory and move future decisions into individual ADRs.

**Exit criteria:** a fresh clone can run formatting, unit tests, and a no-op compose validation without undisclosed local state.

## Phase 1 — Define data contracts and schema migrations

- [ ] Write OpenTelemetry/OpenInference attribute mapping and required/optional-field policy.
- [ ] Add `tenant_id`, environment, agent/version, model/provider, trace/span identifiers, and data-quality flags to the schema.
- [ ] Create migration-managed ClickHouse tables: raw spans, trace rollups, metrics, baselines, findings, analytics job audits.
- [ ] Add partitioning, ordering, TTL, codecs, and indexes based on target query patterns.
- [ ] Version schemas and metric configurations; create a fixture set of representative spans/traces.
- [ ] Verify the selected OTel ClickHouse exporter’s exact table mapping against the pinned collector build.

**Exit criteria:** fixtures ingest successfully and can be queried as complete executions; migrations are repeatable on an empty database.

## Phase 2 — Make ingestion safe and observable

- [ ] Configure collector health, memory limiter, batching, retry queue, backpressure, and diagnostic metrics.
- [ ] Implement secret/PII redaction and payload-size limits before ClickHouse export.
- [ ] Add a sample LangGraph instrumented application and a CrewAI example (or document deferred support if the instrumentation package is incompatible).
- [ ] Add end-to-end tests: emit OTLP → collector → ClickHouse → trace rollup.
- [ ] Measure and report dropped spans, rejected payloads, redaction counts, and ingestion lag.

**Exit criteria:** a sample agent produces an inspectable, redacted execution; an intentional secret never reaches the raw-span table.

## Phase 3 — Build deterministic analytics

- [ ] Implement trace feature extraction: ordered tool path, step count, retries, tokens, duration, error/timeout signals, and cost inputs.
- [ ] Implement embedding adapter with explicit model/dimension/version metadata; support a local/test deterministic adapter.
- [ ] Implement baseline creation, minimum cohort checks, covariance regularization, and baseline approval metadata.
- [ ] Implement `D_M`, `H_amb`, and `V_traj` with unit tests using known numerical fixtures.
- [ ] Persist component values, threshold configuration, metric version, classification, and “insufficient evidence” reasons.
- [ ] Add a scheduled/idempotent analytics job plus audit/logging and rerun support.
- [ ] Validate signal quality with labeled traces and report precision/recall or an explicitly scoped proxy metric.

**Exit criteria:** a fixed fixture corpus produces deterministic, versioned metrics; reruns do not duplicate or alter results unexpectedly.

## Phase 4 — Deliver the investigation API

- [ ] Implement health/readiness, execution list/detail, metric trend, findings, baseline, and configuration endpoints.
- [ ] Publish OpenAPI and generate/use shared request-response contracts.
- [ ] Add pagination, bounded date ranges, query timeout limits, structured error responses, and rate limits.
- [ ] Add authentication and tenant/role authorization before exposing deployment outside a developer machine.
- [ ] Add audit events for baseline/configuration updates and sensitive trace access.

**Exit criteria:** an authenticated user can get from a finding to a single trace and score breakdown through documented APIs only.

## Phase 5 — Build the Agent Lens dashboard

- [ ] Create an executive overview: drift rate, volatility/cost trend, data coverage, top affected agents, and recent findings.
- [ ] Create an investigation view: trace timeline, path comparison, score components, classification rationale, and baseline metadata.
- [ ] Create configuration screens for baseline lifecycle and persisted threshold versions with role restrictions.
- [ ] Add client-side “what-if” controls clearly marked as simulations.
- [ ] Add empty/loading/error states and accessibility checks.

**Exit criteria:** a product owner can navigate trend → finding → execution and understand why the system made its classification.

## Phase 6 — Hardening and operations

- [ ] Add RBAC, audit logs, encryption/secret management, retention tests, and tenant-isolation tests.
- [ ] Define deployment profiles for local Docker, staging, and production Kubernetes/managed ClickHouse.
- [ ] Add load tests for target spans/sec, dashboard query concurrency, and analytics windows.
- [ ] Instrument Agent Lens itself with traces, metrics, logs, and SLO dashboards.
- [ ] Create backup/restore, incident response, data deletion, and upgrade runbooks.

**Exit criteria:** staging meets agreed throughput, privacy, recovery, and observability requirements.

## Deferred capabilities (after the core loop works)

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
