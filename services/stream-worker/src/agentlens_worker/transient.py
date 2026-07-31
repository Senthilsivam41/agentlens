"""Encrypted, short-lived semantic scoring candidates."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from agentlens_contracts import ExecutionFeatures, SamplingDecision, TransientSpan
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, ConfigDict, SecretStr

AAD = b"agentlens.semantic-candidate.v1"
VERSION = b"\x01"


class CandidateExpiredError(ValueError):
    """Raised when transient text outlives the configured privacy TTL."""


class ScoringCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "agentlens.semantic-candidate.v1"
    features: ExecutionFeatures
    sampling: SamplingDecision
    input_text: SecretStr
    output_text: SecretStr
    expires_at: datetime


def candidate_from_trace(
    trace: list[TransientSpan],
    *,
    features: ExecutionFeatures,
    sampling: SamplingDecision,
    ttl: timedelta,
    now: datetime,
) -> ScoringCandidate | None:
    inputs = [span.input_text.get_secret_value() for span in trace if span.input_text]
    outputs = [span.output_text.get_secret_value() for span in trace if span.output_text]
    if not inputs or not outputs:
        return None
    return ScoringCandidate(
        features=features,
        sampling=sampling,
        input_text=SecretStr(inputs[0]),
        output_text=SecretStr(outputs[-1]),
        expires_at=now.astimezone(UTC) + ttl,
    )


def encrypt_candidate(candidate: ScoringCandidate, *, key: str) -> bytes:
    payload: dict[str, Any] = candidate.model_dump(mode="json")
    payload["input_text"] = candidate.input_text.get_secret_value()
    payload["output_text"] = candidate.output_text.get_secret_value()
    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    nonce = os.urandom(12)
    ciphertext = AESGCM(_derive_key(key)).encrypt(nonce, plaintext, AAD)
    return VERSION + nonce + ciphertext


def decrypt_candidate(payload: bytes, *, key: str, now: datetime | None = None) -> ScoringCandidate:
    if len(payload) < 30 or payload[:1] != VERSION:
        raise ValueError("unsupported semantic candidate envelope")
    plaintext = AESGCM(_derive_key(key)).decrypt(payload[1:13], payload[13:], AAD)
    candidate = ScoringCandidate.model_validate_json(plaintext)
    observed_at = (now or datetime.now(UTC)).astimezone(UTC)
    expires_at = candidate.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= observed_at:
        raise CandidateExpiredError("semantic candidate expired")
    return candidate


def _derive_key(value: str) -> bytes:
    if len(value) < 24:
        raise ValueError("transient encryption key must be at least 24 characters")
    return hashlib.sha256(value.encode()).digest()
