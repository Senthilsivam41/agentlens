"""Content-safe hashing helpers."""

from __future__ import annotations

import hashlib
import hmac


def content_hmac(value: str | None, key: bytes) -> str | None:
    if value is None:
        return None
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def event_id(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
