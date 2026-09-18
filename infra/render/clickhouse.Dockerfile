# ClickHouse for Render. The stock server image runs any *.sql placed in
# /docker-entrypoint-initdb.d on first initialization, so we bake the AgentLens
# migrations in. They are idempotent (CREATE ... IF NOT EXISTS, fully-qualified
# names) so re-running is safe.
#
# Build context must be the repository root (dockerContext: .).
FROM clickhouse/clickhouse-server:26.3

COPY db/migrations/*.sql /docker-entrypoint-initdb.d/
