"""Validated CLI import for immutable baseline packages."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .baseline import load_and_fit_package
from .config import WorkerSettings
from .storage import ClickHouseStorage


def import_package(package_dir: Path, settings: WorkerSettings) -> str:
    manifest, artifact = load_and_fit_package(package_dir)
    storage = ClickHouseStorage(settings)
    storage.insert_baseline(manifest, artifact)
    return str(manifest.baseline_id)


def run() -> None:
    parser = argparse.ArgumentParser(
        description="Validate, fit, and register an Agent Lens baseline package"
    )
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    baseline_id = import_package(args.package_dir, WorkerSettings())
    logging.info("baseline imported as candidate: %s", baseline_id)


if __name__ == "__main__":
    run()
