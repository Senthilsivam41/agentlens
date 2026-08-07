# AgentLens OpenInference attribute addendum

Additive attributes on top of [ADR-003](adr/003-otlp-openinference-contract.md) / OpenInference. Do not invent a parallel span taxonomy.

## Required resource attributes (platform-stamped or client-supplied)

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| `agentlens.tenant_id` | string | Platform identity gateway (credential-derived) | Overwrites workload claims (ADR-004) |
| `agentlens.cluster_id` | string | Platform identity gateway (credential-derived) | Overwrites workload claims (ADR-004) |
| `agentlens.identity_source` | string | Platform identity gateway | `collector_credential` when stamped by the gateway |
| `agentlens.agent.name` | string | SDK / adapter | Agent logical name |
| `agentlens.agent.version` | string | SDK / adapter | Agent version |
| `agentlens.framework` | string | SDK / adapter | e.g. `langgraph`, `crewai`, `generic` |

## Baseline reference (ADR-006 / ADR-008)

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| `agentlens.baseline_ref` | string (UUID) | Client SDK / adapter | Equals `baseline_id` of an imported baseline package. Stable client-visible identity for tagging traces against a curated baseline. |

API surfaces the same value as `baseline_ref` on:
- `GET /v1/baselines`
- `GET /v1/baseline-imports/{import_id}` (after validation)
- `POST /v1/baselines/{baseline_id}/activate`

Activation continues to switch the baseline used by **new** scoring jobs only.
