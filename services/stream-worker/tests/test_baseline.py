from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from agentlens_worker.baseline import (
    BaselineValidationError,
    load_and_fit_package,
    manifest_for_records,
)


def test_imported_baseline_is_checksum_validated_and_fitted(tmp_path: Path) -> None:
    package_dir = tmp_path / "baseline"
    package_dir.mkdir()
    records_path = package_dir / "records.parquet"
    rows = [
        {
            "success": True,
            "intent": "lookup" if index < 3 else "update",
            "input_embedding": [1.0 + index / 100, 0.0],
            "output_embedding": [0.0, 1.0 + index / 100],
            "input_entropy": 0.1 + index / 100,
            "tool_path": ["search", "answer"] if index < 3 else ["write"],
        }
        for index in range(6)
    ]
    pq.write_table(pa.Table.from_pylist(rows), records_path)
    manifest = manifest_for_records(
        baseline_id=uuid4(),
        tenant_id="tenant-a",
        environment="test",
        agent_name="agent",
        agent_version="1.0.0",
        model="test-embedding",
        dimensions=2,
        records_path=records_path,
        record_count=len(rows),
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )
    (package_dir / "manifest.json").write_text(manifest.model_dump_json())

    loaded, artifact = load_and_fit_package(package_dir, minimum_records=5)
    assert loaded.baseline_id == manifest.baseline_id
    assert artifact.embedding_dimensions == 2
    assert artifact.drift_threshold >= artifact.distance_mean
    assert artifact.intent_centroids

    (package_dir / "records.parquet").write_bytes(b"tampered")
    with pytest.raises(BaselineValidationError, match="checksum"):
        load_and_fit_package(package_dir, minimum_records=5)
