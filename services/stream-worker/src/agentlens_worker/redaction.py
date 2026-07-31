"""Deterministic defense-in-depth redaction for transient content."""

from __future__ import annotations

import re

MASK = "[REDACTED]"

_PATTERNS = (
    re.compile(
        r"(?i)\b(api[_-]?key|authorization|password|secret|token)\b\s*[:=]\s*['\"]?[^\s,;\"']+"
    ),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]+=*"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
)


def redact_text(value: str | None, *, maximum_length: int = 32768) -> str | None:
    if value is None:
        return None
    redacted = value[:maximum_length]
    for pattern in _PATTERNS:
        redacted = pattern.sub(MASK, redacted)
    return redacted
