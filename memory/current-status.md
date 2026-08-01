# Current Status

**Last updated:** 2026-08-01

**Active branch:** `main`

**HEAD:** `5b4ea0c` (`removed unncessary files and updated gitignore`)

**Repository state:** Runnable production-pilot implementation; pilot hardening remains

## Delivery Status

- Completed implementation phases: Phase 0 through Phase 7 at pilot scope.
- Current implementation phase: Phase 8 pilot hardening.
- Application implementation: end-to-end pilot path is running locally.
- Active blocker: live cloud, identity-provider, embedding-provider, load, security, and recovery acceptance tests need external environments or credentials. The local Helm CLI is unavailable for the current chart-lint rerun.
- Next executable action: automate Kafka outage/replay acceptance, then run the imported-baseline semantic gate with an approved embedding credential.

## Component Status

- Backend: FastAPI service with versioned tenant-scoped APIs, development auth, OIDC JWT validation, RBAC, audit events, query bounds, and rate limiting.
- Frontend: Next.js dashboard with summary, execution, finding, and mathematical-drift views plus OAuth/OIDC routes.
- Stream worker: Redpanda consumers for OTLP normalization, trace assembly, structural scoring, adaptive semantic sampling, encrypted transient candidates, imported baselines, and findings.
- Contracts and SDK: Pydantic contracts plus optional Python instrumentation for LangGraph and CrewAI; plain OTLP/OpenInference remains supported.
- Tests and CI: Python and web test/lint/type/build workflows are present. Latest Python result: 23 tests passed; Ruff and strict mypy passed.
- Docker Compose: runnable API, web, edge/platform OTel collectors, three workers, Redpanda, ClickHouse migrations, and optional MinIO.
- ClickHouse schema: tenant-scoped spans, executions, baseline imports/versions, metric configs, execution scores, findings, stream jobs, and audit events.
- Kubernetes: edge and platform Helm charts include mTLS, persistent edge queueing, health checks, autoscaling, disruption budgets, network policy, ingress, and migrations.
- OTel Collector: edge and shared-platform configurations validate against Collector Contrib `0.157.0`.
- Canonical architecture and development roadmap: present under `docs/`.
- CodeGraph: user reported initialized, but `.codegraph/` remains absent at repository root; repository discovery therefore falls back to normal tools.

## Latest Runtime Evidence

- Local services were healthy: ClickHouse, Redpanda, API, web, edge collector, platform collector, and all three workers.
- Smoke trace `7e8af3143ac6704c1fdc0432089b22f7` traversed OTLP → collectors → Redpanda → workers → ClickHouse.
- The trace reconstructed as one `complete` execution with two steps.
- `GET /health/ready` returned `{"status":"ready"}`.
- `GET /v1/metrics/summary` returned one execution and no semantic score, which is expected without an active imported baseline and embedding credentials.
- `GET /v1/executions?limit=5` returned the reconstructed smoke execution.
- Dashboard root returned HTTP 200.
- Python validation passed: Ruff formatting/lint, strict mypy, and 21 pytest tests.
- Frontend dependencies restored from the frozen lockfile; ESLint, TypeScript, 2 Vitest tests, and the Next.js production build passed.
- A hardened live run emitted three unique traces and passed with 30.423-second p95 freshness, 30 concurrent API requests, three HMAC-bearing durable spans, and zero raw prompt/output marker matches in ClickHouse.
- `scripts/pilot_acceptance.py` now makes the OTLP-to-API freshness, concurrency, and durable-privacy checks repeatable and supports the 1,000 traces/minute target.

## Current Uncommitted Work

- Durable attribute filtering removes known OpenInference, OTel GenAI, and LLM prompt/output content keys before ClickHouse persistence.
- Regression tests cover content filtering and concurrent dashboard API requests.
- The local pilot acceptance runner, Make target, and Phase 8 hardening runbook are new.
- README links the hardening runbook.

## Git State

The active branch is `main` at `5b4ea0c`. The worktree is intentionally dirty with the Phase 8 hardening changes listed above. No commit was created by this session.
