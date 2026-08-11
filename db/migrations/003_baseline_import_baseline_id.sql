ALTER TABLE agentlens.baseline_imports
    ADD COLUMN IF NOT EXISTS baseline_id Nullable(UUID) AFTER validation_errors;

INSERT INTO agentlens.schema_migrations (version) VALUES ('003_baseline_import_baseline_id');
