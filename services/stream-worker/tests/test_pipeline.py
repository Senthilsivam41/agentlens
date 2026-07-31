from datetime import UTC, datetime, timedelta

from agentlens_contracts import Framework, SamplingReason, SpanStatus, TransientSpan
from agentlens_worker import AdaptiveSampler, TraceAssembler, extract_features
from agentlens_worker.durable import to_durable
from agentlens_worker.redaction import redact_text
from agentlens_worker.serialization import transient_span_from_bytes, transient_span_to_bytes
from agentlens_worker.transient import (
    CandidateExpiredError,
    candidate_from_trace,
    decrypt_candidate,
    encrypt_candidate,
)


def span(**updates: object) -> TransientSpan:
    started = datetime(2026, 7, 31, tzinfo=UTC)
    payload: dict[str, object] = {
        "event_id": "event-0000000001",
        "tenant_id": "tenant-a",
        "cluster_id": "cluster-a",
        "environment": "test",
        "service_name": "agent",
        "agent_name": "agent",
        "agent_version": "1.0.0",
        "framework": Framework.LANGGRAPH,
        "trace_id": "a" * 32,
        "span_id": "b" * 16,
        "span_name": "agent.run",
        "started_at": started,
        "ended_at": started + timedelta(seconds=1),
        "status": SpanStatus.OK,
        "input_text": "hello world hello",
        "output_text": "done",
    }
    payload.update(updates)
    return TransientSpan.model_validate(payload)


def test_transient_round_trip_preserves_text_only_explicitly() -> None:
    original = span()
    restored = transient_span_from_bytes(transient_span_to_bytes(original))
    assert restored.input_text is not None
    assert restored.input_text.get_secret_value() == "hello world hello"


def test_assembler_deduplicates_and_flushes_root() -> None:
    now = datetime(2026, 7, 31, tzinfo=UTC)
    assembler = TraceAssembler(
        quiet_period=timedelta(seconds=15), incomplete_timeout=timedelta(minutes=5)
    )
    root = span()
    assert assembler.ingest(root, received_at=now)
    assert not assembler.ingest(root, received_at=now)
    assert assembler.pop_ready(now=now + timedelta(seconds=14)) == []
    ready = assembler.pop_ready(now=now + timedelta(seconds=15))
    assert len(ready) == 1
    assert len(ready[0]) == 1


def test_features_and_sampling_select_error() -> None:
    features = extract_features(
        [span(status=SpanStatus.ERROR, retry_count=2)], hmac_key=b"test-key"
    )
    decision = AdaptiveSampler().decide(features)
    assert features.error_count == 1
    assert features.input_hash != "hello world hello"
    assert decision.selected
    assert decision.reason == SamplingReason.ERROR


def test_redaction_masks_credentials_and_email() -> None:
    value = redact_text("token=abc123 contact person@example.com")
    assert value is not None
    assert "abc123" not in value
    assert "person@example.com" not in value


def test_durable_span_contains_hashes_not_text() -> None:
    durable = to_durable(span(), hmac_key=b"test-key")
    payload = durable.model_dump_json()
    assert "hello world hello" not in payload
    assert durable.input_hash is not None


def test_semantic_candidate_is_encrypted_and_expires() -> None:
    observed_at = datetime(2026, 7, 31, tzinfo=UTC)
    trace = [span()]
    features = extract_features(trace, hmac_key=b"test-key")
    sampling = AdaptiveSampler(normal_sample_rate=1).decide(features)
    candidate = candidate_from_trace(
        trace,
        features=features,
        sampling=sampling,
        ttl=timedelta(minutes=15),
        now=observed_at,
    )
    assert candidate is not None
    key = "test-transient-key-at-least-24-characters"
    encrypted = encrypt_candidate(candidate, key=key)
    assert b"hello world hello" not in encrypted
    restored = decrypt_candidate(encrypted, key=key, now=observed_at)
    assert restored.input_text.get_secret_value() == "hello world hello"
    try:
        decrypt_candidate(encrypted, key=key, now=observed_at + timedelta(minutes=16))
    except CandidateExpiredError:
        pass
    else:
        raise AssertionError("expired semantic text must be rejected")
