"""Config-driven Tier-2 OTel → AgentLens attribute mapping."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import InstrumentationError

# Mirrors infra/otel/agentlens-attribute-mapping.yaml (keep in sync).
DEFAULT_MAPPING: dict[str, Any] = {
    "version": "agentlens.mapping.v1",
    "resource_insert_if_missing": [
        {
            "target": "agentlens.agent.name",
            "sources": ["agentlens.agent.name", "gen_ai.agent.name", "service.name"],
        },
        {
            "target": "agentlens.agent.id",
            "sources": [
                "agentlens.agent.id",
                "gen_ai.agent.id",
                "agentlens.agent.name",
                "service.name",
            ],
        },
        {
            "target": "agentlens.agent.version",
            "sources": ["agentlens.agent.version", "service.version"],
            "default": "unknown",
        },
        {
            "target": "agentlens.framework",
            "sources": ["agentlens.framework"],
            "default": "generic",
        },
        {
            "target": "agentlens.baseline_ref",
            "sources": ["agentlens.baseline_ref"],
        },
    ],
    "span_insert_if_missing": [
        {
            "target": "agentlens.run.id",
            "sources": [
                "agentlens.run.id",
                "gen_ai.response.id",
                "session.id",
                "gcp.vertex.agent.session_id",
            ],
        },
        {
            "target": "tool.name",
            "sources": ["tool.name", "gen_ai.tool.name", "openinference.tool.name"],
        },
        {
            "target": "openinference.tool.name",
            "sources": ["openinference.tool.name", "tool.name", "gen_ai.tool.name"],
        },
        {
            "target": "agentlens.tool.call_id",
            "sources": [
                "agentlens.tool.call_id",
                "gen_ai.tool.call.id",
                "tool.call.id",
            ],
        },
    ],
}

REPO_MAPPING_PATH = (
    Path(__file__).resolve().parents[4] / "infra" / "otel" / "agentlens-attribute-mapping.yaml"
)


def load_mapping(path: Path | None = None) -> dict[str, Any]:
    """Load mapping from YAML when available; otherwise return the baked-in default."""
    mapping_path = path or REPO_MAPPING_PATH
    if mapping_path.is_file():
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise InstrumentationError(
                "PyYAML is required to load Tier-2 attribute mapping files"
            ) from exc
        payload = yaml.safe_load(mapping_path.read_text())
        if not isinstance(payload, dict) or payload.get("version") != "agentlens.mapping.v1":
            raise InstrumentationError(
                "attribute mapping must declare version agentlens.mapping.v1"
            )
        return payload
    return deepcopy(DEFAULT_MAPPING)


def apply_resource_mapping(
    attributes: dict[str, Any], mapping: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Insert AgentLens resource attributes when missing (passthrough Tier 2)."""
    spec = mapping or load_mapping()
    result = dict(attributes)
    for rule in spec.get("resource_insert_if_missing", []):
        target = rule["target"]
        if result.get(target):
            continue
        for source in rule.get("sources", []):
            value = result.get(source)
            if value not in (None, ""):
                result[target] = value
                break
        else:
            default = rule.get("default")
            if default is not None and target not in result:
                result[target] = default
    return result


def apply_span_mapping(
    attributes: dict[str, Any], mapping: dict[str, Any] | None = None
) -> dict[str, Any]:
    spec = mapping or load_mapping()
    result = dict(attributes)
    for rule in spec.get("span_insert_if_missing", []):
        target = rule["target"]
        if result.get(target):
            continue
        for source in rule.get("sources", []):
            value = result.get(source)
            if value not in (None, ""):
                result[target] = value
                break
    return result
