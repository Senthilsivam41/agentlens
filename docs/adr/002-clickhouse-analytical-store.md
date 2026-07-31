# ADR-002: ClickHouse Analytical Store

**Status:** Accepted

ClickHouse stores tenant-scoped span metadata, execution rollups, baselines, scores, findings, and audit events. Schema migrations are owned by Agent Lens. DuckDB may support offline analysis, but production serving reads ClickHouse.

