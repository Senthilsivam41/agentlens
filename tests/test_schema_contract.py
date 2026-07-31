from pathlib import Path


def test_durable_schema_contains_no_raw_prompt_or_output_columns() -> None:
    schema = Path("db/migrations/001_initial.sql").read_text()
    forbidden_columns = ("InputPrompt", "OutputText", "input_text String", "output_text String")
    assert all(column not in schema for column in forbidden_columns)


def test_migration_defines_required_tables() -> None:
    schema = Path("db/migrations/001_initial.sql").read_text()
    required = (
        "agentlens.spans",
        "agentlens.executions",
        "agentlens.baseline_versions",
        "agentlens.execution_scores",
        "agentlens.findings",
        "agentlens.audit_events",
    )
    assert all(table in schema for table in required)
