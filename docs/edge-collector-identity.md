# Edge collector identity contract (ADR-004)

Platform derives `agentlens.tenant_id` and `agentlens.cluster_id` from the **edge collector client certificate**, not from workload or edge-env claims.

## Credential format

Each edge collector must present an mTLS client certificate whose URI SAN is:

```text
spiffe://agentlens/tenant/<tenant_id>/cluster/<cluster_id>
```

Rules:
- `<tenant_id>` and `<cluster_id>` are case-sensitive identifiers matching `[A-Za-z0-9._-]+`
- Exactly one Agent Lens SPIFFE URI SAN is required
- Platform overwrites any inbound `agentlens.tenant_id` / `agentlens.cluster_id` resource attributes with the credential-derived values
- Rewritten batches are stamped with `agentlens.identity_source=collector_credential`

## Helm / deployer checklist

| Value / secret | Purpose |
|----------------|---------|
| `tenantId` / `clusterId` (`infra/k8s/edge/values*.yaml`) | Local labeling only; **not** authoritative in production |
| `existingTlsSecret` (default `agentlens-edge-tls`) | Must contain `tls.crt`, `tls.key`, `ca.crt` with the SPIFFE URI SAN above |
| `platformEndpoint` | Platform collector Service (`…-collector:4318`, OTLP/HTTP) |
| `platformTlsInsecure` | Must be `false` in production |

Platform secret `agentlens-platform-collector-tls` must trust the edge CA (`ca.crt`) and expose the platform server cert/key used by the identity gateway sidecar.

## Trust boundary

1. Edge collector may upsert tenant/cluster from env for local debugging.
2. Identity gateway terminates mTLS, parses the SPIFFE URI SAN, and overwrites resource attributes before forwarding to the in-pod collector on loopback.
3. Platform collector drops traces that lack `agentlens.identity_source=collector_credential`.

Local Compose keeps an insecure collector path without the identity gateway; do not use that path for multi-tenant production.

## Rotation

1. Issue a new edge client certificate with the same SPIFFE URI (or updated tenant/cluster if re-homing).
2. Update `existingTlsSecret` and roll the edge Deployment.
3. Revoke the old cert at the platform CA once the roll completes.
