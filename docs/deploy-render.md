# Deploying Agent Lens on Render

Agent Lens ships a [Render Blueprint](https://render.com/docs/blueprint-spec) (`render.yaml`
at the repo root) that provisions the whole stack directly from the git repository.

## What the blueprint provisions

| Service | Type | Role |
| --- | --- | --- |
| `agentlens-web` | Web (public) | Next.js investigation dashboard |
| `agentlens-api` | Web (public) | FastAPI tenant-scoped API (`/docs`, `/health/ready`) |
| `agentlens-ingest` | Web (public) | Edge OTel collector — OTLP/HTTP trace ingest + redaction |
| `agentlens-otel-platform` | Private | Platform OTel collector — produces to Kafka |
| `agentlens-redpanda` | Private | Kafka API (Redpanda) with a persistent disk |
| `agentlens-clickhouse` | Private | ClickHouse OLAP store with a persistent disk |
| `agentlens-minio` | Private | S3-compatible object store (baseline packages) |
| `agentlens-worker-normalize` | Worker | Normalize raw OTLP spans |
| `agentlens-worker-assemble` | Worker | Assemble spans into executions |
| `agentlens-worker-score` | Worker | Compute drift/ambiguity/volatility scores |
| `agentlens-worker-baseline-import` | Worker | Import/validate baseline packages |

Trace flow: `agent → agentlens-ingest (OTLP/HTTP) → agentlens-otel-platform → Redpanda → normalize → assemble → score → ClickHouse → agentlens-api → agentlens-web`.

## Prerequisites

- A **paid Render workspace**. Private services (`pserv`) and persistent disks are not
  available on the free tier, and this blueprint uses four private services and three disks.
- The repository connected to Render (GitHub/GitLab), or deploy from a public repo URL.

## Deploy

1. In the Render dashboard: **New → Blueprint**, then select this repository/branch. Render
   reads `render.yaml` and shows the services it will create.
2. When prompted for the `sync: false` variables, optionally provide:
   - `OPENAI_API_KEY` on `agentlens-worker-score` — only needed for **semantic** scoring
     (embeddings). Leave blank to run the deterministic/structural path. For OpenRouter or
     another gateway, also add `OPENAI_BASE_URL` on that service.
3. Click **Apply**. Render builds the images and launches all services.

Everything else is wired automatically by the blueprint:

- **Secrets** `CLICKHOUSE_PASSWORD`, `AGENTLENS_HMAC_KEY`, `AGENTLENS_TRANSIENT_KEY`, and the
  MinIO root password are generated once and shared across the services that need them (via a
  shared env group / `generateValue`).
- **Cross-service addresses** (ClickHouse host, Redpanda broker, platform collector, API host)
  are injected with `fromService` references, because Render internal hostnames are dynamic.
- **Schema migrations** in `db/migrations/*.sql` are baked into the ClickHouse image and applied
  automatically on first boot (they are idempotent).
- **Kafka topics** are created on demand — Redpanda runs with `auto_create_topics_enabled=true`.

## After it comes up

- Dashboard: `https://agentlens-web-<suffix>.onrender.com`
- API readiness: `https://agentlens-api-<suffix>.onrender.com/health/ready` → `{"status":"ready"}`
- API docs: `https://agentlens-api-<suffix>.onrender.com/docs`
- OTLP ingest: `https://agentlens-ingest-<suffix>.onrender.com`

### Sending traces (important gRPC caveat)

The public ingest endpoint accepts **OTLP/HTTP** (protobuf over HTTPS on 443). Render does
**not** proxy gRPC end-to-end for public web services (the proxy→service hop is HTTP/1.1), so
the ingest endpoint intentionally exposes OTLP/HTTP, not OTLP/gRPC.

The bundled `agentlens` Python SDK uses the OTLP **gRPC** exporter, so it cannot target the
public Render endpoint directly. To send data to a Render deployment, either:

- point an **OTLP/HTTP** exporter at `https://agentlens-ingest-<suffix>.onrender.com`
  (e.g. a standard OpenTelemetry SDK with `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`), or
- run a local OpenTelemetry Collector next to your agent that receives OTLP/gRPC from the SDK
  and forwards it to the Render ingest over OTLP/HTTP.

(Internal, private-network hops such as edge→platform use gRPC over HTTP/2, which Render's
private network supports — only the public ingest hop is HTTP.)

## Operational notes & caveats

- **Cost**: this is a multi-service stack (3 disks, 4 private services, 3 web services, 4
  workers). Size `plan`/`sizeGB` in `render.yaml` to your needs; ClickHouse and Redpanda default
  to `standard`, the rest to `starter`.
- **No startup ordering**: Render Blueprints don't model `depends_on`. Workers and the API retry
  their ClickHouse/Redpanda connections and Render restarts failed instances, so the stack
  converges once the data services are ready.
- **Single-node data services**: ClickHouse and Redpanda run single-node (dev-grade), matching
  the alpha/local-Compose posture — not an HA production topology.
- **Auth**: `AGENTLENS_AUTH_MODE=dev` (trusted-network mode), same default as local Compose. For
  a real pilot, set `AGENTLENS_AUTH_MODE=oidc` and the `OIDC_*` variables in the dashboard.
- **Baseline import**: `agentlens-minio` is provisioned and the baseline-import worker is pointed
  at it, but importing/activating baselines is an API-driven admin flow (see the main README).

## Validation status

This blueprint has been validated locally as far as is possible without a live Render account:
`render.yaml` parses and matches the Blueprint spec; all four custom images build; the ClickHouse
image auto-applies every migration on first boot; both collector configs pass
`otelcol validate` with the Render env substitutions; Redpanda boots healthy and advertises the
Render discovery hostname; and MinIO starts on its API port. A live end-to-end deploy (private
networking, `fromService` resolution, public routing) must be exercised on your Render workspace
and may need per-workspace tuning (plans, disk sizes, regions).
