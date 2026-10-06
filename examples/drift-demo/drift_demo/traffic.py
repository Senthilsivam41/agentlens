"""Send randomized demo traffic through the local edge collector."""

from __future__ import annotations

import json
import random
from pathlib import Path

from agentlens import instrument
from opentelemetry import trace

from .agent import SupportAgent
from .baseline import cache_dir, load_baseline_id
from .identity import AGENT_NAME, AGENT_VERSION, ENVIRONMENT, SERVICE_NAME
from .prompts import AGENT_REGRESSION, INTENTS, concise_prompt, sample

RUNS_PATH_NAME = "runs.jsonl"


def runs_path() -> Path:
    return cache_dir() / RUNS_PATH_NAME


def send_traffic(
    *,
    endpoint: str,
    count: int,
    vague_ratio: float,
    regression_ratio: float,
    seed: int,
    baseline_ref: str | None = None,
) -> list[dict[str, str]]:
    if not 0 <= regression_ratio <= 1:
        raise ValueError("regression_ratio must be between 0 and 1")
    if count < 1:
        raise ValueError("count must be at least 1")
    resolved_ref = baseline_ref if baseline_ref is not None else load_baseline_id()
    provider = instrument(
        framework="generic",
        agent_name=AGENT_NAME,
        agent_version=AGENT_VERSION,
        environment=ENVIRONMENT,
        service_name=SERVICE_NAME,
        baseline_ref=resolved_ref,
        otlp_endpoint=endpoint,
        insecure=True,
    )
    tracer = trace.get_tracer("agentlens.drift-demo")
    agent = SupportAgent()
    rng = random.Random(seed)
    path = runs_path()
    records: list[dict[str, str]] = []
    try:
        for _ in range(count):
            if rng.random() < regression_ratio:
                intent = rng.choice(INTENTS)
                prompt = concise_prompt(rng, intent)
                scenario = AGENT_REGRESSION
            else:
                drawn = sample(rng, vague_ratio)
                intent = drawn.intent
                prompt = drawn.prompt
                scenario = drawn.scenario
            plan = agent.plan(prompt, scenario, intent)
            trace_id = agent.emit(tracer, plan)
            records.append(
                {
                    "trace_id": trace_id,
                    "scenario": scenario,
                    "intent": intent,
                    "prompt": prompt,
                    "agent_name": AGENT_NAME,
                    "environment": ENVIRONMENT,
                }
            )
    finally:
        provider.force_flush(timeout_millis=10_000)
        provider.shutdown()
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    print(
        f"Sent {len(records)} demo traces as {AGENT_NAME} "
        f"(environment={ENVIRONMENT}) to {endpoint}"
    )
    return records
