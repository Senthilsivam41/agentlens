# Pilot Hardening Runbook

This runbook turns the Phase 8 completion gate into repeatable acceptance evidence. Phase 8 remains incomplete until local and live-cloud gates pass.

**Alpha operator assumptions:** local Compose defaults to `AGENTLENS_AUTH_MODE=dev` (trusted network). Dashboard `/baselines` is read-only; import/activate via API. See [docs/alpha-scope.md](alpha-scope.md).

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

## Recovery and Replay Gate

Run the local outage/replay harness against the Compose stack:

```bash
make pilot-recovery
```

The harness stops the shared platform collector, emits through the edge collector,
and verifies that the file-backed queue grows and replays after recovery. It then
stops Redpanda, emits another trace through the still-running platform collector,
restores the broker, and verifies broker-outage replay. Finally it publishes the
same OTLP protobuf payload twice while normalize/assemble workers are stopped,
restarts those workers with their `earliest` consumer policy, and verifies one
logical execution with two durable spans. Record the JSON output, including queue
batches, queue-file change, both replay latencies, and final execution/span counts.

## Semantic Scoring Acceptance Gate

Use an approved embedding credential only in the shell running the gate; never put
it in a committed file or evidence artifact:

```bash
OPENAI_API_KEY="$APPROVED_EMBEDDING_KEY" make pilot-semantic-acceptance
```

The harness creates a deterministic 500-record `text-embedding-3-small` baseline
package, imports and activates it through the API, emits a trace carrying the
baseline reference, and verifies a complete score uses that baseline and produces
at least one finding. Its JSON output records the baseline ID, score distance,
finding count, and freshness. The acceptance gate is complete only when the
credential-backed run is deterministic and p95 score freshness is below 60 seconds.

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
