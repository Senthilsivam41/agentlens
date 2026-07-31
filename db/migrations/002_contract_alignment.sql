ALTER TABLE agentlens.spans
    ADD COLUMN IF NOT EXISTS schema_version LowCardinality(String) FIRST;

ALTER TABLE agentlens.baseline_versions
    ADD COLUMN IF NOT EXISTS artifact_json String AFTER manifest_json;

INSERT INTO agentlens.schema_migrations (version) VALUES ('002_contract_alignment');
