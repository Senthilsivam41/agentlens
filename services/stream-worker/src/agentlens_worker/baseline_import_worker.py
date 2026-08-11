"""Async validation of pending baseline import packages."""

from __future__ import annotations

import hashlib
import logging
import os
import tarfile
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .baseline import BaselineValidationError, load_and_fit_package
from .config import WorkerSettings
from .storage import ClickHouseStorage

LOGGER = logging.getLogger("agentlens.baseline_import_worker")


class BaselineImportError(ValueError):
    """Raised when a pending baseline import cannot be validated."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_download_url(object_uri: str) -> str:
    parsed = urlparse(object_uri)
    if parsed.scheme in {"http", "https"}:
        return object_uri
    if parsed.scheme == "s3":
        base = os.getenv("AGENTLENS_OBJECT_STORE_HTTP_BASE", "").rstrip("/")
        if not base:
            raise BaselineImportError(
                "s3:// imports require AGENTLENS_OBJECT_STORE_HTTP_BASE to rewrite object URIs"
            )
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        return f"{base}/{bucket}/{key}"
    if parsed.scheme == "file":
        return object_uri
    raise BaselineImportError(f"unsupported object URI scheme: {parsed.scheme}")


def download_package(object_uri: str, destination: Path) -> bytes:
    if object_uri.startswith("file://"):
        source = Path(urlparse(object_uri).path)
        payload = source.read_bytes()
        destination.write_bytes(payload)
        return payload
    url = resolve_download_url(object_uri)
    response = httpx.get(url, timeout=120.0, follow_redirects=True)
    if response.status_code >= 400:
        raise BaselineImportError(f"failed to download package: HTTP {response.status_code}")
    destination.write_bytes(response.content)
    return response.content


def extract_package(archive_path: Path, output_dir: Path) -> Path:
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(output_dir)
    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as archive:
            archive.extractall(output_dir)
    else:
        # Already an unpacked directory copied as a file:// tree marker — treat path as dir root.
        if archive_path.is_dir():
            return archive_path
        raise BaselineImportError("baseline package must be a zip or tar archive")

    manifest_hits = list(output_dir.rglob("manifest.json"))
    if not manifest_hits:
        raise BaselineImportError("extracted package is missing manifest.json")
    return manifest_hits[0].parent


def process_import(
    *,
    storage: ClickHouseStorage,
    import_row: dict[str, Any],
    minimum_records: int = 500,
) -> dict[str, Any]:
    import_id = import_row["import_id"]
    tenant_id = str(import_row["tenant_id"])
    object_uri = str(import_row["object_uri"])
    checksum = str(import_row["checksum"]).lower()
    now = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix="agentlens-baseline-") as tmp:
        tmp_dir = Path(tmp)
        archive_path = tmp_dir / "package.bin"
        try:
            payload = download_package(object_uri, archive_path)
            digest = _sha256_bytes(payload)
            if digest != checksum:
                raise BaselineImportError(
                    "downloaded package checksum does not match import record"
                )
            package_dir = extract_package(archive_path, tmp_dir / "unpacked")
            manifest, artifact = load_and_fit_package(package_dir, minimum_records=minimum_records)
            if manifest.tenant_id != tenant_id:
                raise BaselineImportError("manifest tenant_id does not match import tenant")
            storage.insert_baseline(manifest, artifact)
            updated = {
                **import_row,
                "status": "validated",
                "baseline_id": manifest.baseline_id,
                "validation_errors": [],
                "updated_at": now,
            }
            storage.update_baseline_import(updated)
            LOGGER.info(
                "baseline import %s validated → candidate %s",
                import_id,
                manifest.baseline_id,
            )
            return updated
        except (BaselineImportError, BaselineValidationError, OSError, httpx.HTTPError) as exc:
            updated = {
                **import_row,
                "status": "failed",
                "baseline_id": None,
                "validation_errors": [str(exc)],
                "updated_at": now,
            }
            storage.update_baseline_import(updated)
            LOGGER.warning("baseline import %s failed: %s", import_id, exc)
            return updated


def poll_once(settings: WorkerSettings, *, minimum_records: int = 500) -> int:
    storage = ClickHouseStorage(settings)
    pending = storage.list_pending_baseline_imports(limit=10)
    for row in pending:
        process_import(storage=storage, import_row=row, minimum_records=minimum_records)
    return len(pending)


async def run_poller(settings: WorkerSettings) -> None:
    import asyncio

    interval = max(1, int(os.getenv("AGENTLENS_BASELINE_IMPORT_POLL_SECONDS", "15")))
    minimum_records = int(os.getenv("AGENTLENS_BASELINE_IMPORT_MIN_RECORDS", "500"))
    LOGGER.info("baseline import poller started (interval=%ss)", interval)
    while True:
        try:
            processed = await asyncio.to_thread(
                poll_once, settings, minimum_records=minimum_records
            )
            if processed:
                LOGGER.info("processed %s pending baseline imports", processed)
        except Exception:
            LOGGER.exception("baseline import poller iteration failed")
        await asyncio.sleep(interval)
