"""Imported baseline validation, fitting, and portable artifact serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Self
from uuid import UUID

import numpy as np
import pyarrow.parquet as pq
from agentlens_contracts import BaselineManifest


class BaselineValidationError(ValueError):
    """Raised when an imported baseline package is unsafe or statistically invalid."""


@dataclass(frozen=True, slots=True)
class BaselineArtifact:
    baseline_id: str
    embedding_model: str
    embedding_dimensions: int
    pca_mean: list[float]
    pca_components: list[list[float]]
    tool_vocabulary: list[str]
    mean_vector: list[float]
    inverse_covariance: list[list[float]]
    intent_centroids: list[list[float]]
    distance_mean: float
    distance_stddev: float
    drift_threshold: float
    ambiguity_threshold: float
    ambiguity_alpha: float = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls(**json.loads(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_fit_package(
    package_dir: Path, *, minimum_records: int = 500, maximum_pca_components: int = 64
) -> tuple[BaselineManifest, BaselineArtifact]:
    manifest_path = package_dir / "manifest.json"
    records_path = package_dir / "records.parquet"
    if not manifest_path.is_file() or not records_path.is_file():
        raise BaselineValidationError("baseline package requires manifest.json and records.parquet")
    manifest = BaselineManifest.model_validate_json(manifest_path.read_text())
    if _sha256(records_path) != manifest.records_sha256:
        raise BaselineValidationError("baseline record checksum does not match manifest")
    table = pq.read_table(records_path)
    required = {
        "success",
        "intent",
        "input_embedding",
        "output_embedding",
        "input_entropy",
        "tool_path",
    }
    missing = required.difference(table.column_names)
    if missing:
        raise BaselineValidationError(f"baseline records missing columns: {sorted(missing)}")
    records = [row for row in table.to_pylist() if row["success"]]
    if len(records) < minimum_records:
        raise BaselineValidationError(
            f"baseline requires at least {minimum_records} successful records"
        )
    if manifest.record_count != table.num_rows:
        raise BaselineValidationError("manifest record_count does not match Parquet rows")
    output_embeddings = np.asarray([row["output_embedding"] for row in records], dtype=float)
    input_embeddings = np.asarray([row["input_embedding"] for row in records], dtype=float)
    expected_shape = (len(records), manifest.embedding_dimensions)
    if output_embeddings.shape != expected_shape or input_embeddings.shape != expected_shape:
        raise BaselineValidationError("embedding dimension does not match manifest")
    pca_mean = output_embeddings.mean(axis=0)
    centered = output_embeddings - pca_mean
    component_count = min(maximum_pca_components, len(records) - 1, manifest.embedding_dimensions)
    _, _, right_vectors = np.linalg.svd(centered, full_matrices=False)
    components = right_vectors[:component_count]
    projected = centered @ components.T
    vocabulary = sorted({str(tool) for row in records for tool in (row.get("tool_path") or [])})[
        :32
    ]
    path_matrix = np.asarray(
        [_path_vector(row.get("tool_path") or [], vocabulary) for row in records], dtype=float
    )
    trajectories = np.concatenate([projected, path_matrix], axis=1)
    mean_vector = trajectories.mean(axis=0)
    covariance = np.cov(trajectories, rowvar=False)
    diagonal = np.diag(np.diag(covariance))
    shrunk = 0.9 * covariance + 0.1 * diagonal + np.eye(covariance.shape[0]) * 1e-6
    inverse = np.linalg.pinv(shrunk)
    centered_trajectories = trajectories - mean_vector
    distances = np.sqrt(
        np.maximum(
            0,
            np.einsum(
                "ij,jk,ik->i",
                centered_trajectories,
                inverse,
                centered_trajectories,
            ),
        )
    )
    intents: dict[str, list[np.ndarray[Any, Any]]] = {}
    for row, embedding in zip(records, input_embeddings, strict=True):
        intents.setdefault(str(row["intent"]), []).append(embedding)
    centroids = [np.mean(values, axis=0) for _, values in sorted(intents.items())]
    entropies = np.asarray([float(row["input_entropy"]) for row in records], dtype=float)
    distance_mean = float(distances.mean())
    distance_stddev = float(distances.std())
    artifact = BaselineArtifact(
        baseline_id=str(manifest.baseline_id),
        embedding_model=manifest.embedding_model,
        embedding_dimensions=manifest.embedding_dimensions,
        pca_mean=pca_mean.tolist(),
        pca_components=components.tolist(),
        tool_vocabulary=vocabulary,
        mean_vector=mean_vector.tolist(),
        inverse_covariance=inverse.tolist(),
        intent_centroids=[centroid.tolist() for centroid in centroids],
        distance_mean=distance_mean,
        distance_stddev=distance_stddev,
        drift_threshold=distance_mean + 2.5 * distance_stddev,
        ambiguity_threshold=float(np.quantile(entropies, 0.9)),
    )
    return manifest, artifact


def _path_vector(path: list[str], vocabulary: list[str]) -> list[float]:
    counts = {tool: path.count(tool) for tool in vocabulary}
    denominator = max(len(path), 1)
    known = sum(counts.values())
    return [counts[tool] / denominator for tool in vocabulary] + [
        max(0, len(path) - known) / denominator
    ]


def manifest_for_records(
    *,
    baseline_id: UUID,
    tenant_id: str,
    environment: str,
    agent_name: str,
    agent_version: str,
    model: str,
    dimensions: int,
    records_path: Path,
    record_count: int,
    created_at: Any,
) -> BaselineManifest:
    return BaselineManifest(
        baseline_id=baseline_id,
        tenant_id=tenant_id,
        environment=environment,
        agent_name=agent_name,
        agent_version=agent_version,
        embedding_provider="openai",
        embedding_model=model,
        embedding_dimensions=dimensions,
        record_count=record_count,
        records_sha256=_sha256(records_path),
        created_at=created_at,
    )
