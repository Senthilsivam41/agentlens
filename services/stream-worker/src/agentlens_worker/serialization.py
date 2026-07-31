"""Explicit serialization for sensitive transient events."""

from __future__ import annotations

import json
from typing import Any

from agentlens_contracts import TransientSpan


def transient_span_to_bytes(span: TransientSpan) -> bytes:
    payload: dict[str, Any] = span.model_dump(mode="json")
    payload["input_text"] = span.input_text.get_secret_value() if span.input_text else None
    payload["output_text"] = span.output_text.get_secret_value() if span.output_text else None
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def transient_span_from_bytes(payload: bytes) -> TransientSpan:
    return TransientSpan.model_validate_json(payload)
