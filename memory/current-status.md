# Current Status

**Last updated:** 2026-07-31

**Active branch:** `main`

**HEAD:** `83034e3` (`implementing Pilot version`)

**Repository state:** Runnable production-pilot implementation; pilot hardening remains

## Delivery Status

- Completed implementation phases: Phase 0 through Phase 7 at pilot scope.
- Current implementation phase: Phase 8 pilot hardening.
- Application implementation: end-to-end pilot path is running locally.
- Active blocker: none. Live cloud, identity-provider, embedding-provider, load, security, and recovery acceptance tests still need external environments or credentials.
- Next executable action: restore the interrupted frontend dependency install, rerun frontend validation, then complete the Phase 8 acceptance matrix.

## Component Status

- Backend: FastAPI service with versioned tenant-scoped APIs, development auth, OIDC JWT validation, RBAC, audit events, query bounds, and rate limiting.
- Frontend: Next.js dashboard with summary, execution, finding, and mathematical-drift views plus OAuth/OIDC routes.
- Stream worker: Redpanda consumers for OTLP normalization, trace assembly, structural scoring, adaptive semantic sampling, encrypted transient candidates, imported baselines, and findings.
- Contracts and SDK: Pydantic contracts plus optional Python instrumentation for LangGraph and CrewAI; plain OTLP/OpenInference remains supported.
- Tests and CI: Python and web test/lint/type/build workflows are present. Latest Python result: 21 tests passed; Ruff and strict mypy passed.
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
- Frontend validation had passed earlier, but the final rerun was interrupted while reinstalling locked dependencies; rerun it before claiming the current worktree is fully validated.

## Current Uncommitted Work

- API ClickHouse access is serialized to prevent concurrent reuse of one client session.
- Kafka consumers default to `earliest` so durable groups process records that arrive before first assignment.
- Compose, ClickHouse image/migrations, and schema alignment fixes are pending commit.
- `.pnpm-store/v11/index.db-shm` and `.pnpm-store/v11/index.db-wal` are local install artifacts and must not be committed.

## Git State

The active branch is `main` at `83034e3`. The worktree is intentionally dirty with the runtime fixes and memory updates listed above. No commit was created by this session.
