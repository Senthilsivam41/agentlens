# Current Status

**Last updated:** 2026-08-15

**Active branch:** `codex/build-agent-lens-architecture`

**HEAD:** `3a2d4a1` (`Implement ADR-008 adapter-first instrumentation experience.`)

**Repository state:** Runnable local alpha / pilot implementation. Phase 8 hardening gates remain (especially credential-backed semantic acceptance and live cloud evidence).

## Delivery Status

- Completed implementation phases: Phase 0 through Phase 7 at pilot scope, plus ADR-004 identity gateway, ADR-006 baseline import pipeline + `baseline_ref`, and ADR-008 `agentlens.init()` / adapters / Tier-2 mapping.
- Current implementation phase: Phase 8 pilot hardening.
- Alpha honesty: default auth is `dev`; baselines UI is list-only; semantic drift claim waits on `make pilot-semantic-acceptance` with a real `OPENAI_API_KEY`. See [docs/alpha-scope.md](../docs/alpha-scope.md).
- Active blockers:
  - Semantic acceptance not yet evidenced with an embedding credential in this environment.
  - Live AKS/EKS, real OIDC, mTLS rotation, load/soak, a11y/security/DR reviews still need external environments.
- Next executable action: `OPENAI_API_KEY=… make pilot-semantic-acceptance`, then cloud pilot gates per [docs/pilot-hardening-runbook.md](../docs/pilot-hardening-runbook.md).

## Component Status

- Backend: FastAPI tenant-scoped APIs, `dev` and `oidc` auth modes, RBAC, audit, query bounds, rate limits; baseline import + activate APIs.
- Frontend: Next.js overview, executions, findings, baselines **list** (no import/activate UI).
- Stream worker: normalize, assemble, score, baseline-import modes; identity gateway for mTLS SPIFFE stamping.
- SDK: `agentlens.init()` with langgraph / langchain / crewai / adk / generic; `instrument()` alias; span helpers; Tier-2 mapping helper.
- Compose + Helm: present; local recovery harness has passed previously.
- Docs: README and alpha-scope aligned to remove Text-to-SQL as a shipped headline.

## Latest Runtime Evidence

- Prior local smoke, privacy, concurrency, and recovery harness results remain as recorded historically (see older entries in [completed-actions.md](completed-actions.md)).
- Credential-backed semantic acceptance: **not yet recorded** on current HEAD in this workspace (`OPENAI_API_KEY` absent when last checked).
- GitHub issues #3 (ADR-004), #4 (ADR-006), and #5 (ADR-008) closed as implemented (2026-08-15).

## Git State

Branch `codex/build-agent-lens-architecture` at `3a2d4a1` on origin. Doc/alpha-scope credibility fixes may be in flight as uncommitted work.
