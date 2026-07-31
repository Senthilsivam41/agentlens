FROM clickhouse/clickhouse-server:26.3

COPY migrations /migrations

USER clickhouse
ENTRYPOINT ["/bin/sh", "-ec"]
CMD ["clickhouse-client --host \"$CLICKHOUSE_HOST\" --port \"${CLICKHOUSE_NATIVE_PORT:-9000}\" --user \"$CLICKHOUSE_USERNAME\" --password \"$CLICKHOUSE_PASSWORD\" --multiquery < /migrations/001_initial.sql"]
