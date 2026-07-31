"""Long-running worker entrypoint."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from agentlens_contracts import ScoreStatus
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .assembly import TraceAssembler
from .config import WorkerSettings
from .durable import to_durable
from .embedding import OpenAIEmbeddingClient
from .features import extract_features
from .normalizer import NormalizationError, OtlpNormalizer
from .sampling import AdaptiveSampler
from .scoring import (
    finding_from_score,
    score_execution,
    structural_score,
    unavailable_score,
)
from .serialization import transient_span_from_bytes, transient_span_to_bytes
from .storage import ClickHouseStorage
from .transient import (
    CandidateExpiredError,
    candidate_from_trace,
    decrypt_candidate,
    encrypt_candidate,
)

LOGGER = logging.getLogger("agentlens.worker")


async def normalize(settings: WorkerSettings) -> None:
    consumer = AIOKafkaConsumer(
        settings.kafka_raw_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"{settings.kafka_group_id}-normalize",
        enable_auto_commit=False,
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        compression_type="gzip",
        acks="all",
    )
    normalizer = OtlpNormalizer()
    await consumer.start()
    await producer.start()
    try:
        async for message in consumer:
            try:
                spans = normalizer.normalize(message.value)
                for span in spans:
                    await producer.send_and_wait(
                        settings.kafka_span_topic,
                        transient_span_to_bytes(span),
                        key=f"{span.tenant_id}:{span.cluster_id}:{span.trace_id}".encode(),
                    )
            except NormalizationError as exc:
                await producer.send_and_wait(
                    settings.kafka_dlq_topic,
                    json.dumps({"error": str(exc), "topic": message.topic}).encode(),
                )
            await consumer.commit()
    finally:
        await producer.stop()
        await consumer.stop()


async def assemble(settings: WorkerSettings) -> None:
    consumer = AIOKafkaConsumer(
        settings.kafka_span_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"{settings.kafka_group_id}-assemble",
        enable_auto_commit=False,
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        compression_type="gzip",
        acks="all",
    )
    assembler = TraceAssembler(
        quiet_period=timedelta(seconds=settings.trace_quiet_period_seconds),
        incomplete_timeout=timedelta(seconds=settings.trace_incomplete_timeout_seconds),
    )
    sampler = AdaptiveSampler(normal_sample_rate=settings.semantic_normal_sample_rate)
    storage = ClickHouseStorage(settings)
    hmac_key = settings.agentlens_hmac_key.get_secret_value().encode()
    transient_key = settings.agentlens_transient_key.get_secret_value()
    await consumer.start()
    await producer.start()
    try:
        while True:
            batches = await consumer.getmany(timeout_ms=1000, max_records=500)
            now = datetime.now(UTC)
            received_messages = 0
            durable_spans = []
            for messages in batches.values():
                for message in messages:
                    span = transient_span_from_bytes(message.value)
                    assembler.ingest(span, received_at=now)
                    durable_spans.append(to_durable(span, hmac_key=hmac_key))
                    received_messages += 1
            if durable_spans:
                await asyncio.to_thread(storage.insert_spans, durable_spans)
            for trace in assembler.pop_ready(now=now):
                features = extract_features(trace, hmac_key=hmac_key)
                await asyncio.to_thread(storage.upsert_execution, features)
                decision = sampler.decide(features)
                structural = structural_score(features=features, sampling=decision)
                await asyncio.to_thread(storage.insert_score, structural)
                finding = finding_from_score(structural)
                if finding:
                    await asyncio.to_thread(storage.insert_finding, finding)
                if decision.selected:
                    candidate = candidate_from_trace(
                        trace,
                        features=features,
                        sampling=decision,
                        ttl=timedelta(seconds=settings.transient_ttl_seconds),
                        now=now,
                    )
                    if candidate is None:
                        invalid = unavailable_score(
                            features=features,
                            sampling=decision,
                            status=ScoreStatus.INVALID_INPUT,
                            rationale="selected execution has no input or output text",
                        )
                        await asyncio.to_thread(storage.insert_score, invalid)
                    else:
                        await producer.send_and_wait(
                            settings.kafka_score_topic,
                            encrypt_candidate(candidate, key=transient_key),
                            key=(
                                f"{features.tenant_id}:{features.cluster_id}:{features.trace_id}"
                            ).encode(),
                        )
                LOGGER.info(
                    "execution_ready tenant=%s cluster=%s trace=%s semantic_selected=%s",
                    features.tenant_id,
                    features.cluster_id,
                    features.trace_id,
                    decision.selected,
                )
            if received_messages:
                await consumer.commit()
    finally:
        await producer.stop()
        await consumer.stop()


async def score(settings: WorkerSettings) -> None:
    consumer = AIOKafkaConsumer(
        settings.kafka_score_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"{settings.kafka_group_id}-score",
        enable_auto_commit=False,
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        compression_type="gzip",
        acks="all",
    )
    storage = ClickHouseStorage(settings)
    transient_key = settings.agentlens_transient_key.get_secret_value()
    api_key = settings.openai_api_key.get_secret_value()
    embedder = (
        OpenAIEmbeddingClient(api_key=api_key, model=settings.openai_embedding_model)
        if api_key
        else None
    )
    await consumer.start()
    await producer.start()
    try:
        async for message in consumer:
            try:
                candidate = decrypt_candidate(message.value, key=transient_key)
                features = candidate.features
                baseline = await asyncio.to_thread(
                    storage.active_baseline,
                    tenant_id=features.tenant_id,
                    environment=features.environment,
                    agent_name=features.agent_name,
                    agent_version=features.agent_version,
                )
                if baseline is None:
                    result = unavailable_score(
                        features=features,
                        sampling=candidate.sampling,
                        status=ScoreStatus.INSUFFICIENT_BASELINE,
                        rationale="no active imported baseline matches this execution",
                    )
                elif embedder is None:
                    result = unavailable_score(
                        features=features,
                        sampling=candidate.sampling,
                        status=ScoreStatus.EMBEDDING_UNAVAILABLE,
                        rationale="semantic embedding provider is not configured",
                    )
                else:
                    embeddings = await embedder.embed(
                        [
                            candidate.input_text.get_secret_value(),
                            candidate.output_text.get_secret_value(),
                        ]
                    )
                    result = score_execution(
                        features=features,
                        sampling=candidate.sampling,
                        baseline=baseline,
                        input_embedding=embeddings[0],
                        output_embedding=embeddings[1],
                    )
                await asyncio.to_thread(storage.insert_score, result)
                finding = finding_from_score(result)
                if finding:
                    await asyncio.to_thread(storage.insert_finding, finding)
            except CandidateExpiredError:
                LOGGER.warning("semantic_candidate_expired topic=%s", message.topic)
            except Exception as exc:
                LOGGER.exception("semantic_scoring_failed error_type=%s", type(exc).__name__)
                await producer.send_and_wait(
                    settings.kafka_dlq_topic,
                    json.dumps(
                        {
                            "error": "semantic_scoring_failed",
                            "error_type": type(exc).__name__,
                            "topic": message.topic,
                        }
                    ).encode(),
                )
            await consumer.commit()
    finally:
        await producer.stop()
        await consumer.stop()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = WorkerSettings()
    if settings.worker_mode == "normalize":
        await normalize(settings)
    elif settings.worker_mode == "assemble":
        await assemble(settings)
    else:
        await score(settings)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
