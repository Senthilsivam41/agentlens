import hashlib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from agentlens_contracts import BaselineManifest
from agentlens_worker.baseline import manifest_for_records
from agentlens_worker.baseline_import_worker import process_import, resolve_download_url


class FakeStorage:
    def __init__(self) -> None:
        self.baselines: list[tuple[BaselineManifest, object]] = []
        self.imports: list[dict[str, Any]] = []

    def insert_baseline(self, manifest: BaselineManifest, artifact: object) -> None:
        self.baselines.append((manifest, artifact))

    def update_baseline_import(self, row: dict[str, Any]) -> None:
        self.imports.append(row)


def _package_zip(tmp_path: Path, *, tenant_id: str = "tenant-a") -> tuple[Path, str]:
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
        tenant_id=tenant_id,
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
    archive = tmp_path / "package.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(package_dir / "manifest.json", arcname="manifest.json")
        zipped.write(records_path, arcname="records.parquet")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return archive, digest


def test_resolve_s3_uri_uses_http_base(monkeypatch: Any) -> None:
    monkeypatch.setenv("AGENTLENS_OBJECT_STORE_HTTP_BASE", "https://objects.example")
    assert (
        resolve_download_url("s3://baselines/pkg.zip")
        == "https://objects.example/baselines/pkg.zip"
    )


def test_process_import_validates_and_creates_candidate(tmp_path: Path) -> None:
    archive, digest = _package_zip(tmp_path)
    storage = FakeStorage()
    row = {
        "import_id": uuid4(),
        "tenant_id": "tenant-a",
        "object_uri": archive.resolve().as_uri(),
        "checksum": digest,
        "status": "pending",
        "validation_errors": [],
        "created_by": "admin",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "baseline_id": None,
    }
    updated = process_import(storage=storage, import_row=row, minimum_records=5)  # type: ignore[arg-type]
    assert updated["status"] == "validated"
    assert updated["baseline_id"] is not None
    assert len(storage.baselines) == 1
    assert storage.baselines[0][0].tenant_id == "tenant-a"


def test_process_import_rejects_tenant_mismatch(tmp_path: Path) -> None:
    archive, digest = _package_zip(tmp_path, tenant_id="other-tenant")
    storage = FakeStorage()
    row = {
        "import_id": uuid4(),
        "tenant_id": "tenant-a",
        "object_uri": archive.resolve().as_uri(),
        "checksum": digest,
        "status": "pending",
        "validation_errors": [],
        "created_by": "admin",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "baseline_id": None,
    }
    updated = process_import(storage=storage, import_row=row, minimum_records=5)  # type: ignore[arg-type]
    assert updated["status"] == "failed"
    assert storage.baselines == []
    assert "tenant" in updated["validation_errors"][0]
