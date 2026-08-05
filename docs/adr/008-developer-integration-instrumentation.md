# ADR-008: Developer Integration & Instrumentation Experience

**Status:** Proposed
**Date:** 2026-08-05
**Deciders:** Sendil Sadasivam (project owner)
**Related:**
- [ADR-003](003-otlp-openinference-contract.md) — OTLP transport + OpenInference semantics; this ADR decides *how* adopters get correctly shaped spans into that contract
- [ADR-004](004-edge-collectors-shared-backend.md) — Tier 2 collector passthrough must remain compatible with edge enrichment/redaction
- [ADR-005](005-hash-only-durable-content.md) — adapters/SDK must not encourage durable raw prompt/output retention
- [ADR-006](006-imported-baseline-governance.md) — baselines are addressable imported packages; instrumentation must be able to tag traces with a baseline reference once activation identity is exposed to clients

## Context

AgentLens's core value (drift detection across ClickHouse/OTel/DuckDB) is only useful if agent developers can get traces into the system with minimal friction. ADR-003 already locks the wire contract (OTLP + OpenInference) and allows an optional Python SDK, but does not decide the *adoption path*: adapters vs. manual SDK vs. collector-only.

Without that front-door decision, there is a risk of shipping a powerful backend that nobody adopts because integration stays bespoke per agent framework.

This mirrors a failure mode Sendil has seen firsthand on `dual-llm-router`: pairing a planner/executor pipeline (Hermes 4 + Laguna S 2.1 via OpenRouter/LiteLLM on ADK 2.0) required hand-wiring orchestration glue rather than dropping in a standard adapter. AgentLens should not force every adopter to repeat that cost.

Forces at play:
- Target users are agent developers already using LangChain, LlamaIndex, CrewAI, or ADK — few will hand-instrument OTel spans.
- Local-first trialability matters: DuckDB exists specifically so someone can evaluate AgentLens without standing up ClickHouse (ADR-002).
- Drift detection formulas need consistent, well-shaped span/event data — a loose "send us whatever" ingestion contract undermines detection quality later.
- ADR-003's OpenInference baseline must remain the semantic foundation; AgentLens-specific required attributes (e.g. baseline reference) are additive, not a parallel schema.
- This is a pre-code, architecture-review-stage decision; the integration strategy here is load-bearing for adapter work and for how clients attach to ADR-006 baselines.

## Decision

Adopt a **three-tier instrumentation strategy**, in priority order, all converging on ADR-003's OTLP + OpenInference contract plus a small set of AgentLens-required attributes:

1. **Auto-instrumentation via framework adapters** (primary path) — thin adapter packages for LangChain, LlamaIndex, CrewAI, and ADK 2.0 that wrap agent execution and emit OTel spans conforming to OpenInference + AgentLens required attributes, without manual span code.
2. **OTel collector passthrough** (secondary path) — for teams already emitting OTel traces from custom agents, accept standard OTLP export (including via ADR-004 edge collectors) and map known span attributes into the AgentLens-required set via a defined, config-driven mapping.
3. **Manual SDK** (fallback path) — `agentlens.init()` + explicit span helpers for anything the adapters don't cover, kept as a thin wrapper over the OTel SDK rather than a parallel API surface. Correctly instrumented OTLP clients still need no AgentLens dependency (ADR-003).

All three tiers converge on one attribute contract so drift formulas never special-case the ingestion source.

## Options Considered

### Option A: Adapter-first (chosen)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — N adapters to build and maintain against upstream framework churn |
| Cost | Low ongoing infra cost; engineering cost is adapter maintenance |
| Scalability | High — OTel is the transport regardless of tier |
| Team familiarity | High — Sendil has direct ADK 2.0 and LangGraph/hybrid-RAG experience from kinegraph-v and Polaris Neuro Guard |

**Pros:** Fastest path to "traces flowing" for the frameworks target users actually use; matches how OTel-native LLM observability tools have won adoption; extends ADR-003 rather than replacing it.
**Cons:** Adapter maintenance burden grows with each framework version bump; risk of adapter lag behind upstream releases.

### Option B: Manual-SDK-only
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low to build, high for adopters |
| Cost | Low |
| Scalability | High |
| Team familiarity | High |

**Pros:** Simplest to build and maintain; no adapter-drift risk.
**Cons:** Repeats the bespoke-wiring pain from `dual-llm-router`; high adoption friction; most developers won't hand-instrument.

### Option C: OTel-passthrough-only, no adapters
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Cost | Low |
| Scalability | High |
| Team familiarity | Medium |

**Pros:** Leans entirely on the OTel ecosystem; no framework-specific code to maintain.
**Cons:** Assumes adopters already have OTel instrumented, which most agent-framework users don't by default; pushes integration cost onto every adopter.

## Trade-off Analysis

Option A costs more upfront (adapters to build and keep current) but is the only option that removes the adoption barrier for the primary audience (agent framework users). Option B is cheapest to build but shifts all integration cost to adopters — unacceptable given AgentLens's goal of being a hands-on bridge into the agentic ecosystem. Option C is retained as Tier 2, but cannot be the only path.

The real risk in Option A is maintenance drift as LangChain/LlamaIndex/CrewAI/ADK ship breaking changes. Mitigate by keeping adapters thin (pure span-emission wrappers, no business logic) and pinning supported framework version ranges explicitly rather than chasing every release.

This ADR does **not** reopen ADR-003's transport/semantics choice; it only prioritizes delivery mechanisms that produce compliant telemetry.

## Consequences

- **Easier:** New adopters get traces flowing in minutes via an adapter; drift formulas get consistently shaped OpenInference + AgentLens-attribute data regardless of tier.
- **Harder:** Adapter surface area grows with each supported framework; version compatibility testing becomes an ongoing CI concern.
- **Constrained by ADR-005:** Adapters and the manual SDK must document and default to hash/redaction-safe emission paths; they must not become a backdoor for durable raw content.
- **Dependent on ADR-006:** Baseline tagging requires a stable client-visible baseline reference (imported package / activated version identity). Field name and shape are confirmed against ADR-006 before adapters ship — not invented independently here.
- **To revisit:** If OpenInference coverage gaps force AgentLens-specific span names beyond additive attributes, document those extensions in the semantic-convention doc and note divergence from ADR-003's "OpenInference supplies semantics" stance.
- **Deferred, not decided here:** CLI (`agentlens trace tail`, `agentlens drift check`), webhook/alerting integrations, and trace-replay UX — scope in a follow-up ADR (ADR-009 candidate) once Tier 1 adapters exist.

## Action Items

1. [ ] Define the AgentLens attribute addendum to OpenInference (required attributes: `agent_id`, `run_id`, baseline reference aligned with ADR-006, tool-call metadata) as a standalone schema doc before writing adapter code — do not invent a parallel span taxonomy
2. [ ] Build the ADK 2.0 adapter first (highest familiarity; reuse Polaris Neuro Guard / dual-llm-router learnings)
3. [ ] Build LangChain adapter second (largest addressable user base)
4. [ ] Define Tier 2 OTel collector mapping rules as config-driven (compatible with ADR-004 edge collectors), not hardcoded
5. [ ] Write `agentlens.init()` manual SDK as a thin OTel wrapper validated against the same OpenInference + AgentLens attribute contract used by adapters
6. [ ] Cross-check baseline-reference field name/shape against ADR-006 (imported package identity and activated version) before locking the schema doc
7. [ ] Defer CLI/webhook/replay scope to ADR-009 (candidate)
