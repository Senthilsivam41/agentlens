# AgentLens OpenInference attribute addendum

Additive attributes on top of [ADR-003](adr/003-otlp-openinference-contract.md) / OpenInference.
Do **not** invent a parallel span taxonomy. Tier-1 adapters, Tier-2 collector mapping, and
`agentlens.init()` all converge on this contract ([ADR-008](adr/008-developer-integration-instrumentation.md)).

## Required resource attributes

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| `agentlens.tenant_id` | string | Platform identity gateway (credential-derived) | Overwrites workload claims ([ADR-004](adr/004-edge-collectors-shared-backend.md)) |
| `agentlens.cluster_id` | string | Platform identity gateway (credential-derived) | Overwrites workload claims (ADR-004) |
| `agentlens.identity_source` | string | Platform identity gateway | `collector_credential` when stamped by the gateway |
| `agentlens.agent.name` | string | SDK / adapter | Agent logical name |
| `agentlens.agent.id` | string | SDK / adapter | Stable agent identity; defaults to `agentlens.agent.name` |
| `agentlens.agent.version` | string | SDK / adapter | Agent version |
| `agentlens.framework` | string | SDK / adapter | `langgraph` \| `langchain` \| `crewai` \| `adk` \| `generic` |

## Required / recommended span attributes

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| `agentlens.run.id` | string (UUID preferred) | SDK / adapter / Tier-2 mapping | Correlates one agent execution |
| `tool.name` | string | OpenInference / GenAI / Tier-2 mapping | Preferred tool name key for normalizer |
| `openinference.tool.name` | string | OpenInference | Alias accepted by ingestion |
| `agentlens.tool.call_id` | string | SDK / adapter | Optional per-call identifier |

## Baseline reference ([ADR-006](adr/006-imported-baseline-governance.md) / ADR-008)

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| `agentlens.baseline_ref` | string (UUID) | Client SDK / adapter | **Equals `baseline_id`** of an imported baseline package. Locked after ADR-006 import/activate API. |

API surfaces the same value as `baseline_ref` on:
- `GET /v1/baselines`
- `GET /v1/baseline-imports/{import_id}` (after validation)
- `POST /v1/baselines/{baseline_id}/activate`

Activation continues to switch the baseline used by **new** scoring jobs only.

## Privacy ([ADR-005](adr/005-hash-only-durable-content.md))

Adapters and `agentlens.init()` must not encourage durable raw prompt/output retention.
ADK adapter defaults `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` and
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT`.

## Tier-2 mapping

Config-driven insert-if-missing rules live in:
- `infra/otel/agentlens-attribute-mapping.yaml` (source of truth)
- `infra/otel/processors/agentlens-attribute-mapping.yaml` (collector transform fragment)
- `agentlens.mapping` Python applicator for tests / offline validation
