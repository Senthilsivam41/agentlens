# Goldfish Annotated Review Report

**Status:** resolved
**Target:** [`2026-11-04_DRIFT_REPORT.md`](/Users/sendils/work/repo/agent-observability/agentlens/2026-11-04_DRIFT_REPORT.md) (`full file`)
**Resolution:** 21 accepted, 0 contested, 0 escalated, 0 declined, 0 remaining.

All findings below are valid repository-grounded divergences. They are classified as `PROPOSE FIX`; no finding is contested, escalated, or declined. Proposed edits prefer the smallest change that makes the documented contract truthful. Implementation additions are proposed only for the collector mapping and sampling paths where the current contract explicitly promises behavior.

## Prioritized Findings & AI Suggestions

### [Issue 1] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 11-13 ([2026-11-04_DRIFT_REPORT.md#L11-L13](2026-11-04_DRIFT_REPORT.md#L11-L13)) (`agent-drift-dashboard/architecture.md`)
*   **Discrepancy Description:** The legacy design specifies daily/nightly DuckDB plus NumPy/SciPy batch processing, direct ClickHouse ingestion, legacy table names, raw prompt/output/vector columns, Text-to-SQL, and live what-if sliders, while the implementation uses Redpanda/Kafka stream workers, the current ClickHouse schema, hash-only durable content, and an API-only baseline flow.
*   **Rationale:** The repository contains a newer streaming/hash-only implementation and `docs/alpha-scope.md` explicitly defers Text-to-SQL and dashboard baseline controls.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The document is a legacy design but is not labelled as superseded, so readers can mistake target-state claims for supported behavior.
*   ***Proposed Edit:***
    *   Location: `agent-drift-dashboard/architecture.md`, immediately after the title.
    *   Change: Add a `Status: Legacy target architecture — not the current alpha implementation` banner linking to `docs/agentlens-architecture.md`, `README.md`, and `docs/alpha-scope.md`; label DuckDB/SciPy, legacy tables, raw content, Text-to-SQL, and what-if controls as future alternatives rather than current components.

### [Issue 2] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 54-57 ([2026-11-04_DRIFT_REPORT.md#L54-L57](2026-11-04_DRIFT_REPORT.md#L54-L57)) (`docs/agentlens-architecture.md`)
*   **Discrepancy Description:** The blueprint specifies scheduled DuckDB/SciPy batch analytics, a ClickHouse-compatible collector exporter, opt-in durable raw content, cost metadata, payload-size limits, and deletion workflows that are not implemented.
*   **Rationale:** The live path is Redpanda/Kafka streaming, the collector exports to Kafka, durable storage is hash-only, cost fields are absent, and no deletion endpoint or explicit collector payload limit exists.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The canonical architecture document must describe the current alpha contract and clearly separate post-pilot requirements.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-architecture.md`, system diagram, principles, telemetry collector, analytics worker, data boundary, and retention/security sections.
    *   Change: Replace the current-path claims with the implemented edge/platform collector → Kafka/Redpanda → normalize/assemble/score → ClickHouse flow; state that durable content is hash-only with encrypted transient semantic candidates; mark cost accounting, explicit payload limits, deletion workflows, and scheduled DuckDB/SciPy analysis as post-pilot backlog items.

### [Issue 3] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 41-42 ([2026-11-04_DRIFT_REPORT.md#L41-L42](2026-11-04_DRIFT_REPORT.md#L41-L42)) (`docs/adr/007-adaptive-semantic-sampling.md`)
*   **Discrepancy Description:** The ADR promises `UNKNOWN_PATH` and `NEW_VERSION` triggers and per-score sampling coverage, but the live assembly path does not pass known sets and the persisted score schema has no coverage field.
*   **Rationale:** `services/stream-worker/src/agentlens_worker/main.py` calls `sampler.decide(features)`; `sampling.py` accepts known sets but no caller supplies them; `db/migrations/001_initial.sql` has no coverage column.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The contract currently overstates runtime behavior. The smallest safe fix is to make the ADR match the implemented alpha behavior rather than invent an ungoverned source for known paths or a new schema field.
*   ***Proposed Edit:***
    *   Location: `docs/adr/007-adaptive-semantic-sampling.md`, decision and storage statements.
    *   Change: State that the sampler supports optional known-path/version inputs, but the alpha worker currently enables error, timeout, volatility, and deterministic normal sampling only; state that coverage is an API-level aggregate until a versioned per-score field is approved.

### [Issue 4] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 46 ([2026-11-04_DRIFT_REPORT.md#L46](2026-11-04_DRIFT_REPORT.md#L46)) (`docs/adr/008-developer-integration-instrumentation.md`)
*   **Discrepancy Description:** The accepted ADR decision includes a LlamaIndex adapter, but the SDK has no LlamaIndex activator or optional dependency; the alpha scope lists LlamaIndex as deferred.
*   **Rationale:** `packages/sdk-python/src/agentlens/adapters/__init__.py` exposes LangGraph, LangChain, CrewAI, ADK, and generic activation only; `packages/sdk-python/pyproject.toml` has no LlamaIndex extra.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The ADR and alpha scope must not make contradictory support claims.
*   ***Proposed Edit:***
    *   Location: `docs/adr/008-developer-integration-instrumentation.md`, decision and action-item sections.
    *   Change: Change LlamaIndex from an accepted alpha adapter to a post-pilot/backlog adapter, while retaining the implemented LangGraph/LangChain/CrewAI/ADK/generic paths.

### [Issue 5] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 61-64 ([2026-11-04_DRIFT_REPORT.md#L61-L64](2026-11-04_DRIFT_REPORT.md#L61-L64)) (`docs/agentlens-development-roadmap.md`)
*   **Discrepancy Description:** The roadmap says the repository has only drafts and no functional backend, frontend, workers, tests, manifests, or pipeline; it also retains the old DuckDB/SciPy topology, old Phase 5 UI goals, and unchecked phase boxes despite Phases 0-7 being implemented and Phase 8 being active.
*   **Rationale:** `memory/next-plans.md` records Phases 0-7 complete and Phase 8 in progress; the corresponding source directories and test suites exist.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This is materially misleading project status and can cause duplicate implementation work.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-development-roadmap.md`, repository assessment and phase table.
    *   Change: Replace the initial scaffold assessment with the current runnable-alpha assessment; update the topology to streaming workers; mark Phases 0-7 `complete`, Phase 8 `in-progress`, and post-pilot items `not-started`; move what-if controls and other deferred items to the post-pilot section.

### [Issue 6] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 97-99 ([2026-11-04_DRIFT_REPORT.md#L97-L99](2026-11-04_DRIFT_REPORT.md#L97-L99)) (`docs/product-positioning-and-ecosystem-integration.md`)
*   **Discrepancy Description:** The product strategy describes an AutoClaw/file bridge, lifecycle event contract, broader framework adapters, and coordination dashboards/findings that are not implemented.
*   **Rationale:** The current SDK and UI expose runtime OTLP/SDK instrumentation, executions, scores, findings, baselines, and summaries; the report itself records no bridge or coordination data plane.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The strategy is valid as a roadmap, but its implementation status must be explicit.
*   ***Proposed Edit:***
    *   Location: `docs/product-positioning-and-ecosystem-integration.md`, status/roadmap and ecosystem matrix sections.
    *   Change: Add `Proposed / post-pilot` labels to the AutoClaw bridge, lifecycle event plane, coordination dashboards, and OpenAI Agents SDK/Microsoft Agent Framework/Semantic Kernel/AutoGen adapters; mark the currently shipped LangGraph/LangChain/CrewAI/ADK/generic OTLP paths separately.

### [Issue 7] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 88-89 ([2026-11-04_DRIFT_REPORT.md#L88-L89](2026-11-04_DRIFT_REPORT.md#L88-L89)) (`docs/openinference-attribute-addendum.md`)
*   **Discrepancy Description:** The mapping source of truth includes fallbacks for `service.name`, `gcp.vertex.agent.session_id`, `agentlens.tool.call_id`, and `tool.call.id`, but collector transform fragments omit several of them.
*   **Rationale:** The omissions are visible in `infra/otel/processors/agentlens-attribute-mapping.yaml`, `infra/otel/edge-config.yaml`, `infra/k8s/edge/files/collector.yaml`, and `infra/render/edge-config.yaml`.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Collector-side generic OTLP producers can lose correlation and identity attributes even though the documented mapping promises those fallbacks.
*   ***Proposed Edit:***
    *   Location: All collector transform fragments listed in the rationale.
    *   Change: Add the missing `agentlens.agent.id ← service.name`, `agentlens.run.id ← gcp.vertex.agent.session_id`, and `agentlens.tool.call_id ← tool.call.id` insert-if-missing statements; keep the YAML source-of-truth and fragments synchronized with a focused config test.

### [Issue 8] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 88-89 ([2026-11-04_DRIFT_REPORT.md#L88-L89](2026-11-04_DRIFT_REPORT.md#L88-L89)) (`infra/otel/edge-local-config.yaml`)
*   **Discrepancy Description:** The local Compose edge collector has no `transform/agentlens_mapping` processor, so generic OTLP sent through that path bypasses the documented Tier-2 mapping.
*   **Rationale:** `edge-local-config.yaml` contains receivers, redaction, identity, batching, and export, but no transform processor or pipeline reference.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Local and Kubernetes/Render producer behavior should not silently differ for generic OTLP.
*   ***Proposed Edit:***
    *   Location: `infra/otel/edge-local-config.yaml`, processors and traces pipeline.
    *   Change: Include the shared AgentLens transform statements after redaction and add `transform/agentlens_mapping` to the traces processor list; validate the collector configuration and add a mapping regression fixture.

### [Issue 9] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 11-13 ([2026-11-04_DRIFT_REPORT.md#L11-L13](2026-11-04_DRIFT_REPORT.md#L11-L13)) (`agent-drift-dashboard/architecture.md`)
*   **Discrepancy Description:** The legacy document separately claims a Text-to-SQL gateway and client-side sensitivity sliders that are absent and deferred.
*   **Rationale:** `docs/alpha-scope.md` explicitly excludes Text-to-SQL and dashboard baseline controls from alpha.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** These claims should be visibly future-state rather than appearing in the active target architecture.
*   ***Proposed Edit:***
    *   Location: `agent-drift-dashboard/architecture.md`, Text-to-SQL and dashboard sections.
    *   Change: Prefix both capabilities with `Post-pilot proposal — not implemented` and link to `docs/alpha-scope.md`.

### [Issue 10] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 56-57 ([2026-11-04_DRIFT_REPORT.md#L56-L57](2026-11-04_DRIFT_REPORT.md#L56-L57)) (`docs/agentlens-architecture.md`)
*   **Discrepancy Description:** Cost currency/rate fields, explicit payload-size limits, and tenant deletion workflows are described as requirements but do not exist in the current contracts/schema/API.
*   **Rationale:** The current contract and API expose no cost fields, payload-limit setting, or deletion route.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** These are meaningful product/security requirements, but adding them without a versioned contract and acceptance test would be larger than this drift repair.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-architecture.md`, minimum ingestion contract and security requirements.
    *   Change: Mark cost attribution, configurable payload limits, and tenant deletion as explicit Phase 8/post-pilot backlog items with acceptance gates; do not present them as implemented alpha behavior.

### [Issue 11] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 54-55 ([2026-11-04_DRIFT_REPORT.md#L54-L55](2026-11-04_DRIFT_REPORT.md#L54-L55)) (`docs/agentlens-architecture.md`)
*   **Discrepancy Description:** The canonical blueprint says the collector exports directly to ClickHouse and permits raw content opt-in, but the implementation exports to Kafka and uses hash-only durable storage with encrypted transient semantic candidates.
*   **Rationale:** `infra/otel/platform-config.yaml` exports traces to Kafka; `durable.py` removes content attributes before ClickHouse insertion.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The privacy and ingestion boundaries are central to the product and must be unambiguous.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-architecture.md`, system diagram, data boundary, and retention table.
    *   Change: Replace direct ClickHouse/raw-content language with Kafka-backed streaming and hash-only durable storage; describe encrypted transient content only for sampled semantic scoring.

### [Issue 12] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 7 ([2026-11-04_DRIFT_REPORT.md#L7](2026-11-04_DRIFT_REPORT.md#L7)) (`README.md`)
*   **Discrepancy Description:** The README architecture diagram does not distinguish the production identity-gateway path from the local Compose path, which intentionally omits the gateway.
*   **Rationale:** `docs/edge-collector-identity.md` states that local Compose is insecure/local-only and has no identity gateway.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** A reader following the README could assume local Compose provides production tenant identity guarantees.
*   ***Proposed Edit:***
    *   Location: `README.md`, architecture heading and diagram caption.
    *   Change: Label the diagram `Platform/Kubernetes deployment path` and add a note that local Compose uses an insecure edge-to-platform path without the identity gateway.

### [Issue 13] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 61-62 ([2026-11-04_DRIFT_REPORT.md#L61-L62](2026-11-04_DRIFT_REPORT.md#L61-L62)) (`docs/agentlens-development-roadmap.md`)
*   **Discrepancy Description:** The roadmap still plans scheduled DuckDB/SciPy analytics while the implemented workers normalize, assemble, and score through Redpanda/Kafka.
*   **Rationale:** The current worker entrypoint and Compose topology use Kafka topics and stream workers.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The roadmap should sequence work against the implementation that will actually be piloted.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-development-roadmap.md`, analytics and worker tasks.
    *   Change: Replace scheduled DuckDB/SciPy tasks with the implemented streaming pipeline and retain DuckDB/SciPy as optional offline/post-pilot analysis.

### [Issue 14] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 63 ([2026-11-04_DRIFT_REPORT.md#L63](2026-11-04_DRIFT_REPORT.md#L63)) (`docs/agentlens-development-roadmap.md`)
*   **Discrepancy Description:** Phase 5 requires client-side what-if controls and baseline lifecycle screens, but the current UI is read-only and the alpha scope makes baseline import/activation API-only.
*   **Rationale:** `apps/web/app/baselines/page.tsx` lists versions only; `docs/alpha-scope.md` documents the API-only boundary.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The roadmap should not make a deferred UI feature appear to be a missing implementation prerequisite for the current pilot.
*   ***Proposed Edit:***
    *   Location: `docs/agentlens-development-roadmap.md`, Phase 5.
    *   Change: Mark what-if controls and dashboard baseline mutation as post-pilot candidates; define the Phase 5 gate using the existing import/activate API and read-only listing.

### [Issue 15] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 84 ([2026-11-04_DRIFT_REPORT.md#L84](2026-11-04_DRIFT_REPORT.md#L84)) (`docs/live-demo.md`)
*   **Discrepancy Description:** The troubleshooting section instructs `make live-demo --skip-compose`, but the Make target does not forward arguments.
*   **Rationale:** `Makefile` invokes `uv run python scripts/live_demo.py --mode full` without `--skip-compose`; the Python script supports the flag directly.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This is a directly reproducible user-facing command failure.
*   ***Proposed Edit:***
    *   Location: `docs/live-demo.md`, troubleshooting command.
    *   Change: Replace `make live-demo --skip-compose` with `uv run python scripts/live_demo.py --mode full --skip-compose`, or add a dedicated Make target whose command explicitly passes the flag.

### [Issue 16] [`egm-drift-report`] - Severity: Major

*   **Affected Scope:** Lines 97-98 ([2026-11-04_DRIFT_REPORT.md#L97-L98](2026-11-04_DRIFT_REPORT.md#L97-L98)) (`docs/product-positioning-and-ecosystem-integration.md`)
*   **Discrepancy Description:** The product strategy proposes a broad ecosystem matrix, but only LangGraph, LangChain, CrewAI, ADK, and generic OTLP activation exist in the SDK.
*   **Rationale:** The SDK optional dependencies and activators contain no OpenAI Agents SDK, Microsoft Agent Framework/Semantic Kernel, AutoGen, or LlamaIndex implementation.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This can be resolved without building four adapters by separating current support from future ecosystem targets.
*   ***Proposed Edit:***
    *   Location: `docs/product-positioning-and-ecosystem-integration.md`, ecosystem matrix.
    *   Change: Add `status`/`availability` labels and mark unsupported framework rows as `planned/post-pilot`; retain generic OTLP as the current integration path.

### [Issue 17] [`egm-drift-report`] - Severity: Nit

*   **Affected Scope:** Lines 41-42 ([2026-11-04_DRIFT_REPORT.md#L41-L42](2026-11-04_DRIFT_REPORT.md#L41-L42)) (`docs/adr/007-adaptive-semantic-sampling.md`)
*   **Discrepancy Description:** The persisted score stores sampling policy and reason but not a per-score coverage value.
*   **Rationale:** The current API computes semantic coverage as an aggregate rather than reading a score-level field.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The wording should describe the actual aggregate coverage boundary until a schema change is deliberately approved.
*   ***Proposed Edit:***
    *   Location: `docs/adr/007-adaptive-semantic-sampling.md`, score persistence paragraph.
    *   Change: Replace “every score stores coverage” with “the API reports aggregate semantic coverage; per-score coverage is reserved for a future schema revision.”

### [Issue 18] [`egm-drift-report`] - Severity: Nit

*   **Affected Scope:** Lines 7 ([2026-11-04_DRIFT_REPORT.md#L7](2026-11-04_DRIFT_REPORT.md#L7)) (`README.md`)
*   **Discrepancy Description:** The README diagram is ambiguous about which deployment path includes the identity gateway.
*   **Rationale:** The local exception is documented only in a separate identity document.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** A short caption prevents an avoidable security misunderstanding.
*   ***Proposed Edit:***
    *   Location: `README.md`, immediately below the architecture diagram.
    *   Change: Add one sentence distinguishing platform/Kubernetes mTLS identity from local Compose development identity.

### [Issue 19] [`egm-drift-report`] - Severity: Nit

*   **Affected Scope:** Lines 11 ([2026-11-04_DRIFT_REPORT.md#L11](2026-11-04_DRIFT_REPORT.md#L11)) (`agent-drift-dashboard/architecture.md`)
*   **Discrepancy Description:** The old architecture is not visibly marked as historical, so its legacy schemas and topology can be read as active design.
*   **Rationale:** The repository has a newer canonical architecture and active alpha scope.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** A status banner is the smallest safe repair and avoids deleting potentially useful historical design context.
*   ***Proposed Edit:***
    *   Location: `agent-drift-dashboard/architecture.md`, title block.
    *   Change: Add a visible legacy/superseded status banner with links to the current architecture and alpha scope.

### [Issue 20] [`egm-drift-report`] - Severity: Nit

*   **Affected Scope:** Lines 97-99 ([2026-11-04_DRIFT_REPORT.md#L97-L99](2026-11-04_DRIFT_REPORT.md#L97-L99)) (`docs/product-positioning-and-ecosystem-integration.md`)
*   **Discrepancy Description:** Proposed orchestration-plane and coordination-dashboard capabilities are not implemented.
*   **Rationale:** The current UI/API is runtime execution, score, finding, baseline, and summary oriented.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** The strategy should preserve these as roadmap value without implying they are shipped.
*   ***Proposed Edit:***
    *   Location: `docs/product-positioning-and-ecosystem-integration.md`, opening status paragraph and roadmap table.
    *   Change: Add a clear `strategy/proposed` label and mark implementation status for every coordination-plane capability.

### [Issue 21] [`egm-drift-report`] - Severity: Nit

*   **Affected Scope:** Lines 84 ([2026-11-04_DRIFT_REPORT.md#L84](2026-11-04_DRIFT_REPORT.md#L84)) (`docs/live-demo.md`)
*   **Discrepancy Description:** The documented Make invocation does not match the supported script invocation.
*   **Rationale:** The direct Python command is already supported and requires no new dependency or abstraction.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Correcting the one command is lower-risk than changing Make argument forwarding semantics.
*   ***Proposed Edit:***
    *   Location: `docs/live-demo.md`, troubleshooting section.
    *   Change: Use the direct script command with `--skip-compose` and retain `make live-demo` for the normal full path.
