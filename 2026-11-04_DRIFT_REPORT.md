# Agent Lens Drift Report — 2026-11-04

Scope: design documents and README files under this repository. Operational `memory/` files and generated `graphify-out/` artifacts were excluded. Each section records only document-to-implementation divergences; a clean section means no drift detected.

## README.md

- The architecture diagram presents a platform collector and identity gateway as the general ingestion path, while the local Compose path has no identity gateway and is intentionally documented elsewhere as an insecure local-only path. The README should label the diagram as the platform deployment path or show the local exception.

## agent-drift-dashboard/architecture.md

- This legacy design specifies daily/nightly DuckDB plus NumPy/SciPy batch processing, direct ClickHouse ingestion, `otel_agent_spans`/`agent_drift_metrics` tables, and raw prompt/output/vector columns. The implementation uses Redpanda/Kafka stream workers, the `agentlens.spans`/execution/score schema, and hash-only durable content; those batch topology, table, and raw-content claims are not implemented.
- The proposed FastAPI Instructor/LangChain Text-to-SQL gateway is absent and explicitly deferred in the current alpha scope.
- The proposed live client-side sensitivity/what-if sliders are absent; the current baseline page is read-only and baseline import/activation is API-driven.

## docs/adr/001-asynchronous-deterministic-evaluation.md

No drift detected.

## docs/adr/002-clickhouse-analytical-store.md

No drift detected.

## docs/adr/003-otlp-openinference-contract.md

No drift detected.

## docs/adr/004-edge-collectors-shared-backend.md

No drift detected.

## docs/adr/005-hash-only-durable-content.md

No drift detected.

## docs/adr/006-imported-baseline-governance.md

No drift detected.

## docs/adr/007-adaptive-semantic-sampling.md

- The ADR promises `UNKNOWN_PATH` and `NEW_VERSION` sampling triggers, but the live assembly path calls `AdaptiveSampler.decide(features)` without passing `known_tool_paths` or `known_agent_versions`; those triggers are therefore unreachable in production unless a caller supplies them elsewhere.
- The ADR states that every score stores sampling coverage, but the persisted score contract/schema does not contain a per-score coverage field; coverage is calculated at the API summary level instead.

## docs/adr/008-developer-integration-instrumentation.md

- The accepted decision includes a LlamaIndex adapter, but the SDK has no LlamaIndex activator or optional dependency. The alpha scope correctly lists LlamaIndex as deferred, so the ADR decision and alpha scope disagree.

## docs/adr/README.md

No drift detected.

## docs/agentlens-architecture.md

- The blueprint specifies scheduled DuckDB plus NumPy/SciPy batch analytics and a ClickHouse-compatible collector exporter. The implementation runs Redpanda/Kafka streaming workers and the collector exports to Kafka; no DuckDB/SciPy scheduled analytics job is present.
- The blueprint permits raw content opt-in after redaction, while the implemented durable boundary always removes known prompt/output content attributes and retains HMAC hashes; the current behavior is stricter than the blueprint.
- The blueprint’s cost currency/rate metadata and cost-aware feature fields are not represented in the contracts, durable span model, execution features, or ClickHouse schema.
- The blueprint requires tested payload-size limits and deletion workflows. No explicit collector payload-size limit or tenant deletion API/workflow is implemented.

## docs/agentlens-development-roadmap.md

- The repository assessment is stale: it says only drafts exist and that backend, frontend, worker, tests, manifests, and pipeline are absent, while those components now exist under `apps/`, `services/`, `packages/`, `infra/`, and `tests/`.
- The roadmap’s planned scheduled DuckDB/SciPy analytics topology differs from the implemented Redpanda streaming worker topology.
- Phase 5 calls for client-side what-if controls and baseline lifecycle screens; the current web UI is read-only for baselines and the alpha scope documents import/activation as API-only.
- All roadmap phase checkboxes remain unchecked even though multiple implementation phases have been completed, so the roadmap does not reflect current execution status.

## docs/alpha-scope.md

No drift detected.

## docs/deploy-render.md

No drift detected.

## docs/deploy/README.md

No drift detected.

## docs/edge-collector-identity.md

No drift detected.

## docs/live-demo.md

- The troubleshooting section instructs `make live-demo --skip-compose`, but the `live-demo` Make target does not forward arguments and always invokes `scripts/live_demo.py --mode full`. `--skip-compose` works when invoking the Python script directly or via the dedicated check target, not through the documented Make command.

## docs/openinference-attribute-addendum.md

- The declared source-of-truth mapping includes `gen_ai.agent.id` and `service.name` fallbacks for `agentlens.agent.id`, `gcp.vertex.agent.session_id` for `agentlens.run.id`, and `agentlens.tool.call_id`/`tool.call.id` mappings. The collector transform fragment omits the `service.name` agent-id fallback, the Vertex session-id fallback, and the canonical `agentlens.tool.call_id` source; the Kubernetes edge fragment repeats the omissions.
- `infra/otel/edge-local-config.yaml` has no `transform/agentlens_mapping` processor, so generic OTLP sent through the local Compose edge path does not apply the documented collector-side Tier-2 mapping.

## docs/pilot-hardening-runbook.md

No drift detected.

## docs/product-positioning-and-ecosystem-integration.md

- The proposed orchestration telemetry plane and AutoClaw bridge (file tail/watermark consumer, lifecycle event contract, and correlation pipeline) are not implemented; the repository currently provides runtime OTLP/SDK instrumentation only.
- The ecosystem matrix proposes OpenAI Agents SDK, Microsoft Agent Framework/Semantic Kernel, and AutoGen adapters, but the SDK currently exposes LangGraph, LangChain, CrewAI, Google ADK, and generic OTLP activation.
- Coordination-specific dashboards, findings, and metrics described by the product strategy are absent; the current UI/API covers runtime executions, scores, findings, baselines, and summaries.

## examples/adk/README.md

No drift detected.

## examples/crewai/README.md

No drift detected.

## examples/drift-demo/README.md

No drift detected.

## examples/langchain/README.md

No drift detected.

## examples/langgraph/README.md

No drift detected.
