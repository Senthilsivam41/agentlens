# Locked Decisions

**Last updated:** 2026-07-31

**Status:** Accepted unless explicitly marked superseded

## Product and Delivery

- Target: production pilot.
- Delivery assumption: three engineers across twelve two-week sprints.
- Pilot load: 1,000 traces per minute.
- Selected semantic-score freshness: p95 under 60 seconds.
- Text-to-SQL: post-pilot.

## Integration and Deployment

- Agent interface: standard OTLP plus OpenInference semantics.
- Client experience: optional Agent Lens Python SDK; plain OTLP remains supported.
- Topology: local edge collectors with a shared Agent Lens backend.
- Platforms: AKS, EKS, and generic Kubernetes.
- Framework order: LangGraph first; CrewAI required before pilot exit.
- User identity: OIDC JWT.
- Collector identity: mTLS; shared gateway derives and overwrites tenant/cluster identity.
- Deployment targets: Docker Compose and Kubernetes.

## Data, Privacy, and Streaming

- Tenancy: tenant-ready core with enforced query and ingestion scoping.
- Durable prompt/output storage: HMAC-SHA256 hashes only.
- Transient content: redacted, encrypted, retained for no more than 15 minutes.
- Stream transport: Redpanda.
- Semantic scoring coverage: adaptive sampling.
- Structural scoring coverage: every eligible completed trace.

## Analytics

- Initial embedding provider: OpenAI.
- Initial embedding model: `text-embedding-3-small`.
- Baseline source: imported, externally curated datasets only.
- Baseline activation: validated immutable versions with explicit administration.
- Evaluation path: deterministic mathematical scoring; no inline LLM-as-a-judge requirement.
