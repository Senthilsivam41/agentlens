CREATE DATABASE IF NOT EXISTS agentlens;

CREATE TABLE IF NOT EXISTS agentlens.schema_migrations
(
    version String,
    applied_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(applied_at)
ORDER BY version;

CREATE TABLE IF NOT EXISTS agentlens.spans
(
    event_id String,
    tenant_id LowCardinality(String),
    cluster_id LowCardinality(String),
    cloud_provider LowCardinality(String),
    cloud_region LowCardinality(Nullable(String)),
    environment LowCardinality(String),
    service_name LowCardinality(String),
    agent_name LowCardinality(String),
    agent_version LowCardinality(String),
    framework LowCardinality(String),
    trace_id String,
    span_id String,
    parent_span_id Nullable(String),
    span_name String,
    started_at DateTime64(6, 'UTC') CODEC(DoubleDelta, ZSTD),
    ended_at DateTime64(6, 'UTC') CODEC(DoubleDelta, ZSTD),
    duration_ms Float64,
    status LowCardinality(String),
    graph_node Nullable(String),
    tool_name LowCardinality(Nullable(String)),
    model_name LowCardinality(Nullable(String)),
    prompt_tokens UInt64,
    completion_tokens UInt64,
    retry_count UInt32,
    input_hash Nullable(String),
    output_hash Nullable(String),
    attributes_json String CODEC(ZSTD),
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64 DEFAULT toUnixTimestamp64Milli(ingested_at)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(started_at)
ORDER BY (tenant_id, environment, agent_name, toDate(started_at), trace_id, span_id)
TTL started_at + INTERVAL 30 DAY DELETE;

CREATE TABLE IF NOT EXISTS agentlens.executions
(
    tenant_id LowCardinality(String),
    cluster_id LowCardinality(String),
    environment LowCardinality(String),
    agent_name LowCardinality(String),
    agent_version LowCardinality(String),
    trace_id String,
    started_at DateTime64(6, 'UTC'),
    ended_at DateTime64(6, 'UTC'),
    data_quality LowCardinality(String),
    step_count UInt32,
    total_tokens UInt64,
    duration_ms Float64,
    total_retries UInt32,
    error_count UInt32,
    timeout_count UInt32,
    tool_path Array(String),
    tool_retry_counts_json String,
    input_hash Nullable(String),
    output_hash Nullable(String),
    input_entropy Nullable(Float64),
    trajectory_volatility Nullable(Float64),
    feature_version LowCardinality(String),
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3),
    version UInt64 DEFAULT toUnixTimestamp64Milli(updated_at)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(started_at)
ORDER BY (tenant_id, environment, agent_name, toDate(started_at), trace_id)
TTL started_at + INTERVAL 90 DAY DELETE;

CREATE TABLE IF NOT EXISTS agentlens.baseline_imports
(
    import_id UUID,
    tenant_id LowCardinality(String),
    object_uri String,
    checksum String,
    status LowCardinality(String),
    validation_errors Array(String),
    created_by String,
    created_at DateTime64(3, 'UTC') DEFAULT now64(3),
    updated_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (tenant_id, import_id);

CREATE TABLE IF NOT EXISTS agentlens.baseline_versions
(
    baseline_id UUID,
    tenant_id LowCardinality(String),
    environment LowCardinality(String),
    agent_name LowCardinality(String),
    agent_version LowCardinality(String),
    status LowCardinality(String),
    embedding_provider LowCardinality(String),
    embedding_model LowCardinality(String),
    embedding_dimensions UInt32,
    record_count UInt64,
    feature_dimension UInt32,
    mean_vector Array(Float64),
    inverse_covariance Array(Array(Float64)),
    pca_mean Array(Float64),
    pca_components Array(Array(Float64)),
    intent_centroids_json String,
    thresholds_json String,
    manifest_json String,
    artifact_json String,
    created_at DateTime64(3, 'UTC'),
    activated_at Nullable(DateTime64(3, 'UTC')),
    retired_at Nullable(DateTime64(3, 'UTC')),
    version UInt64 DEFAULT toUnixTimestamp64Milli(created_at)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (tenant_id, environment, agent_name, agent_version, baseline_id);

CREATE TABLE IF NOT EXISTS agentlens.metric_configs
(
    config_id UUID,
    tenant_id LowCardinality(String),
    metric_version LowCardinality(String),
    status LowCardinality(String),
    config_json String,
    created_by String,
    created_at DateTime64(3, 'UTC'),
    activated_at Nullable(DateTime64(3, 'UTC')),
    version UInt64 DEFAULT toUnixTimestamp64Milli(created_at)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (tenant_id, metric_version, config_id);

CREATE TABLE IF NOT EXISTS agentlens.execution_scores
(
    score_id UUID,
    tenant_id LowCardinality(String),
    cluster_id LowCardinality(String),
    trace_id String,
    baseline_id Nullable(UUID),
    metric_version LowCardinality(String),
    status LowCardinality(String),
    sampling_policy LowCardinality(String),
    sampling_reason LowCardinality(String),
    mahalanobis_distance Nullable(Float64),
    ambiguity_score Nullable(Float64),
    trajectory_volatility Nullable(Float64),
    drift_threshold Nullable(Float64),
    ambiguity_threshold Nullable(Float64),
    is_drifted Nullable(Bool),
    root_cause LowCardinality(String),
    rationale Array(String),
    computed_at DateTime64(3, 'UTC'),
    version UInt64 DEFAULT toUnixTimestamp64Milli(computed_at)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(computed_at)
ORDER BY (tenant_id, trace_id, metric_version, score_id)
TTL computed_at + INTERVAL 13 MONTH DELETE;

CREATE TABLE IF NOT EXISTS agentlens.findings
(
    finding_id UUID,
    tenant_id LowCardinality(String),
    cluster_id LowCardinality(String),
    trace_id String,
    score_id UUID,
    severity LowCardinality(String),
    root_cause LowCardinality(String),
    title String,
    rationale Array(String),
    state LowCardinality(String),
    created_at DateTime64(3, 'UTC'),
    updated_at DateTime64(3, 'UTC'),
    version UInt64 DEFAULT toUnixTimestamp64Milli(updated_at)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(created_at)
ORDER BY (tenant_id, state, created_at, finding_id)
TTL created_at + INTERVAL 13 MONTH DELETE;

CREATE TABLE IF NOT EXISTS agentlens.stream_jobs
(
    job_id UUID,
    worker_id String,
    topic String,
    partition Int32,
    offset Int64,
    status LowCardinality(String),
    error_code Nullable(String),
    started_at DateTime64(3, 'UTC'),
    completed_at Nullable(DateTime64(3, 'UTC'))
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(started_at)
ORDER BY (topic, partition, offset, started_at);

CREATE TABLE IF NOT EXISTS agentlens.audit_events
(
    audit_id UUID,
    tenant_id LowCardinality(String),
    actor_id String,
    actor_roles Array(String),
    action LowCardinality(String),
    resource_type LowCardinality(String),
    resource_id String,
    details_json String,
    occurred_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (tenant_id, occurred_at, audit_id)
TTL occurred_at + INTERVAL 13 MONTH DELETE;

INSERT INTO agentlens.schema_migrations (version) VALUES ('001_initial');
