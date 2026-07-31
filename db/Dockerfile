FROM clickhouse/clickhouse-server:26.3

COPY migrations /migrations

USER clickhouse
ENTRYPOINT ["/bin/sh", "-ec"]
CMD ["for migration in /migrations/*.sql; do clickhouse-client --host \"$CLICKHOUSE_HOST\" --port \"${CLICKHOUSE_NATIVE_PORT:-9000}\" --user \"$CLICKHOUSE_USERNAME\" --password \"$CLICKHOUSE_PASSWORD\" --multiquery < \"$migration\"; done"]
