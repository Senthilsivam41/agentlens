# Current Status

**Last updated:** 2026-08-11

**Active branch:** `codex/build-agent-lens-architecture`

**HEAD:** `82a92f2` (`Implement ADR-004 credential identity and ADR-006 baseline import pipeline.`)

**Repository state:** Runnable production-pilot implementation with local recovery acceptance automated; pilot hardening remains

## Delivery Status

- Completed implementation phases: Phase 0 through Phase 7 at pilot scope.
- Current implementation phase: Phase 8 pilot hardening.
- Application implementation: end-to-end pilot path is running locally.
- Active blocker: semantic acceptance needs an approved `OPENAI_API_KEY`; live cloud identity-provider, mTLS, load, security, accessibility, and disaster-recovery gates still need external environments. The local Helm CLI is unavailable for the current chart-lint rerun.
- Next executable action: run `make pilot-semantic-acceptance` with the approved embedding credential, then repeat the recovery gate in the target AKS/EKS environment.

## Component Status

- Backend: FastAPI service with versioned tenant-scoped APIs, development auth, OIDC JWT validation, RBAC, audit events, query bounds, and rate limiting.
- Frontend: Next.js dashboard with summary, execution, finding, and mathematical-drift views plus OAuth/OIDC routes.
- Stream worker: Redpanda consumers for OTLP normalization, trace assembly, structural scoring, adaptive semantic sampling, encrypted transient candidates, imported baselines, and findings; Compose now includes a dedicated baseline-import worker.
- Contracts and SDK: Pydantic contracts plus optional Python instrumentation for LangGraph and CrewAI; plain OTLP/OpenInference remains supported.
- Tests and CI: Python and web test/lint/type/build workflows are present. Latest Python result: 31 tests passed; Ruff and strict mypy across source, workers, and acceptance scripts passed.
- Docker Compose: runnable API, web, edge/platform OTel collectors, four workers including baseline import, Redpanda, ClickHouse migrations, and optional MinIO; edge queue metrics are exposed locally on port 18889.
- ClickHouse schema: tenant-scoped spans, executions, baseline imports/versions, metric configs, execution scores, findings, stream jobs, and audit events.
- Kubernetes: edge and platform Helm charts include mTLS, persistent edge queueing, health checks, autoscaling, disruption budgets, network policy, ingress, and migrations.
- OTel Collector: edge and shared-platform configurations validate against Collector Contrib `0.157.0`.
- Canonical architecture and development roadmap: present under `docs/`.
- Product positioning and ecosystem strategy: proposed under `docs/`, with agent-synthetix/AutoClaw as the first reference control-plane integration; no adapter implementation has been completed.
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
- `scripts/pilot_recovery.py` passed locally: edge queue increased from 0 to 1 batch, the persistent queue file changed, edge replay completed in 37.989 seconds, Redpanda outage replay completed in 22.702 seconds, duplicate replay completed in 24.197 seconds, and ClickHouse contained 1 final execution with 2 durable spans.
- `scripts/semantic_acceptance.py` is implemented and statically validated; its seeded 500-record/1536-dimension package fits successfully, but its credential-backed run is not claimed: `OPENAI_API_KEY` was absent and the script exited with its explicit credential requirement.

## Current Uncommitted Work

- Durable attribute filtering removes known OpenInference, OTel GenAI, and LLM prompt/output content keys before ClickHouse persistence.
- Regression tests cover content filtering and concurrent dashboard API requests.
- The local pilot acceptance runner, recovery/replay runner, semantic acceptance runner, Make targets, queue metrics, and Phase 8 hardening runbook are present.
- Current changes are uncommitted; `graphify-out/` is an unrelated user-generated untracked directory.

## Git State

The active branch is `codex/build-agent-lens-architecture` at `82a92f2`. The worktree is intentionally dirty with the Phase 8 hardening changes listed above and the user-generated `graphify-out/` directory. No commit was created by this session.
