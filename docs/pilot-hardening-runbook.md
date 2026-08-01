# Pilot Hardening Runbook

This runbook turns the Phase 8 completion gate into repeatable acceptance evidence. Phase 8 remains incomplete until local and live-cloud gates pass.

## Local Automated Gate

Start the Compose stack using `.env`, then run:

```bash
make pilot-acceptance
```

The command emits a unique OTLP/OpenInference trace and verifies:

- the execution becomes queryable before the 60-second freshness deadline;
- concurrent readiness, summary, and execution API requests succeed;
- unique prompt/output markers never appear in durable ClickHouse attributes;
- durable spans retain 64-character HMAC values instead of raw content.

Use the production target rate for a one-minute load gate:

```bash
uv run python scripts/pilot_acceptance.py --count 1000 --traces-per-minute 1000
```

Record the JSON output and worker/API/ClickHouse resource metrics with the pilot evidence. The encrypted transient TTL is enforced by unit tests and Kafka `retention.ms=900000`; inspect broker topic configuration during environment acceptance.

## Live AKS/EKS Gate

For each approved pilot environment:

1. Install the platform chart and the matching `values-aks.yaml` or `values-eks.yaml` edge overlay.
2. Validate collector client-certificate rejection, acceptance, and rotation.
3. Stop platform ingestion, emit traffic for the agreed outage window, restore ingestion, and prove edge-queue replay without duplicate executions.
4. Validate OIDC issuer, audience, expiry, role enforcement, and cross-tenant denial using the real identity provider.
5. Import and activate a fixed baseline, then record deterministic semantic scores and findings using the approved embedding credential.
6. Run the 1,000 traces/minute load for at least one hour and a lower-rate soak for 24 hours.
7. Restore ClickHouse from backup into an isolated namespace and execute the rollback procedure.
8. Run WCAG 2.2 AA automated checks and keyboard/screen-reader journeys for every dashboard route.

## Evidence Record

For each run, capture date, environment, Git SHA, chart/app versions, operator, exact command, result, p50/p95/p99 freshness, error rate, resource saturation, privacy query results, recovery point/time, and artifact links. Add only successful, evidenced actions to `memory/completed-actions.md`; keep failed or pending gates in `memory/current-status.md` and `memory/next-plans.md`.
