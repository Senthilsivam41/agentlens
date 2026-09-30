# Railway deployment

Hosted Agent Lens on Railway. This is the alpha dashboard plus API and ClickHouse. It is not the full Compose stack: Redpanda, stream workers, collectors, and MinIO are not deployed.

Local Compose remains the path for ingestion and scoring. See the [README quick start](../../README.md#quick-start-local-compose).

## Open the project

| | |
| --- | --- |
| Workspace project | [agentlens](https://railway.com/project/aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7?environmentId=6286b50f-52f2-479b-9aa6-80d5711d92f0) |
| Project ID | `aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7` |
| Environment | `production` (`6286b50f-52f2-479b-9aa6-80d5711d92f0`) |
| Region | `sfo` |
| Dashboard | https://agentlens-production-dcb0.up.railway.app |

Sign in to Railway, then open the project link. The environment selector should read **production**.

From this repo, point the CLI at the same project:

```bash
railway link --project aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7 --environment production
railway service list --json --environment production
```

## What is running

| Service | Role | Source | Public URL |
| --- | --- | --- | --- |
| `agentlens` | Next.js dashboard | `apps/web/Dockerfile` | https://agentlens-production-dcb0.up.railway.app |
| `api` | FastAPI | `apps/api/Dockerfile` | none (private) |
| `clickhouse` | ClickHouse 26.3 | image `clickhouse/clickhouse-server:26.3` | none (private) |

Service pages:

- [agentlens](https://railway.com/project/aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7/service/bd6c6068-ab34-49e8-af2f-2623196d2e02?environmentId=6286b50f-52f2-479b-9aa6-80d5711d92f0)
- [api](https://railway.com/project/aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7/service/0813e80d-f10c-47b3-9b31-fbdec62b0dbc?environmentId=6286b50f-52f2-479b-9aa6-80d5711d92f0)
- [clickhouse](https://railway.com/project/aeffbfc3-4d71-4ff5-a3da-fe853d31b4e7/service/7dec4d62-a919-4808-bae7-4ab1a2090acb?environmentId=6286b50f-52f2-479b-9aa6-80d5711d92f0)

ClickHouse data is on volume `clickhouse-volume`, mounted at `/var/lib/clickhouse` (500 MB).

The dashboard calls the API over the private network:

```text
AGENTLENS_API_URL=http://api.railway.internal:8000
```

The API reaches ClickHouse at `clickhouse.railway.internal:8123`, database `agentlens`, user `agentlens`. The password is a Railway variable, not a value in this repo:

```bash
railway variable list --service api --environment production --json
```

`AGENTLENS_AUTH_MODE=dev` with tenant `local` and roles `viewer,analyst,admin`. The public dashboard does not show a login page. Treat the URL as a trusted-network pilot, same as local alpha. See [alpha scope](../alpha-scope.md).

## Use the dashboard

Open https://agentlens-production-dcb0.up.railway.app.

| Page | Path |
| --- | --- |
| Overview | `/` |
| Executions | `/executions` |
| One execution | `/executions/<traceId>` |
| Baselines | `/baselines` |

Overview, Executions, and Baselines read the API from the Next.js server. An empty project shows zeros or an empty list. A banner or failed page load means the API or ClickHouse query failed; check the logs in the next section.

Baselines stay read-only in the UI. Import and activate baselines through the API.

## Check health

Deployment status:

```bash
railway service list --json --environment production
```

Each service should show `"status": "SUCCESS"` and one running replica.

Runtime logs:

```bash
railway logs --service agentlens --environment production --lines 100
railway logs --service api --environment production --lines 100
railway logs --service clickhouse --environment production --lines 100
```

The API process listens on port 8000 inside the private network. It has no public domain. To call health checks from a laptop, add one and target that port:

```bash
railway domain --service api --port 8000 --environment production --json
curl -sS https://<api-domain>/health/live
curl -sS https://<api-domain>/health/ready
```

| Endpoint | Expected |
| --- | --- |
| `/health/live` | `{"status":"ok"}` |
| `/health/ready` | `{"status":"ready"}` |

`/health/live` only means the process is up. `/health/ready` returns 503 when ClickHouse is unreachable or the schema is missing. Schema SQL is in `db/migrations/` and is applied by `db/Dockerfile` in Compose. This Railway project has no migrations service (the account service limit is three). Until those SQL files are applied, ready-checks and dashboard queries can fail even though the containers are running.

ClickHouse stays private. From a machine with a Railway SSH key (`railway ssh keys add`):

```bash
railway ssh --service clickhouse --environment production -- \
  sh -c 'clickhouse-client --user agentlens --password "$CLICKHOUSE_PASSWORD" --query "SELECT 1"'
```

Do not attach a public domain to `clickhouse`.

## Redeploy

From the repo root, after `railway link`:

```bash
railway up --service api --environment production --detach -m "Deploy AgentLens API"
railway up --service agentlens --environment production --detach -m "Deploy AgentLens dashboard"
```

Build settings are on the services, not in a committed config file:

- `api` builder `DOCKERFILE`, path `apps/api/Dockerfile`
- `agentlens` builder `DOCKERFILE`, path `apps/web/Dockerfile`

Both Dockerfiles use the repository root as the build context. Upload the repo root; do not upload `apps/api` or `apps/web` alone.

A detached `railway up` only queues the build. Wait until `railway deployment list --service <name> --environment production --json` shows `SUCCESS` before treating it as deployed.
