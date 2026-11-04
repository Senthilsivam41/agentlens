"""Offline checks for the customer drift demo."""

from __future__ import annotations

import random

import numpy as np
import pytest
from agentlens_worker.features import shannon_entropy
from drift_demo.agent import SupportAgent, features_for
from drift_demo.client import RateLimited
from drift_demo.prompts import (
    _RAMBLING_BANK,
    AGENT_REGRESSION,
    CLEAR,
    INTENTS,
    TOOL_FAILURE,
    VAGUE_CLARIFY_LOOP,
    VAGUE_RAMBLING,
    VAGUE_SCENARIOS,
    baseline_prompt,
    sample,
)
from drift_demo.report import collect_scores


def test_sampler_is_deterministic_and_honors_vague_ratio() -> None:
    assert _sequence(7) == _sequence(7)

    rng = random.Random(3)
    draws = [sample(rng, 0.4) for _ in range(2000)]
    vague = sum(item.scenario != CLEAR for item in draws) / len(draws)
    assert abs(vague - 0.4) < 0.05

    only_clear = [sample(random.Random(9 + index), 0) for index in range(40)]
    assert {item.scenario for item in only_clear} == {CLEAR}


def test_loop_volatility_and_tool_failure_features() -> None:
    agent = SupportAgent()
    for intent in INTENTS:
        clear = features_for(agent.plan("Where is order A1001 shipping today?", CLEAR, intent))
        assert clear.trajectory_volatility is not None
        assert clear.trajectory_volatility < 4
        assert clear.error_count == 0

        loop = features_for(agent.plan("fix it", VAGUE_CLARIFY_LOOP, intent))
        assert loop.trajectory_volatility is not None
        assert loop.trajectory_volatility >= 4
        assert loop.error_count == 0
        assert len(loop.tool_path) >= 9

    failure = features_for(agent.plan("update the account", TOOL_FAILURE, "account_change"))
    assert failure.error_count > 0

    regression = agent.plan(
        "Track order A1001 for ada@example.com.",
        AGENT_REGRESSION,
        "order_status",
    )
    clear = agent.plan(regression.prompt, CLEAR, regression.intent)
    assert regression.tool_path == ["escalate_human", "legacy_crm"]
    assert regression.output != clear.output


def test_clear_prompts_sit_below_entropy_percentile_and_rambling_above() -> None:
    assert len(_RAMBLING_BANK) >= 42
    assert len(set(_RAMBLING_BANK)) == len(_RAMBLING_BANK)

    rng = random.Random(0)
    baseline = [baseline_prompt(rng)[1] for _ in range(500)]
    entropies = [shannon_entropy(prompt) for prompt in baseline]
    assert all(value is not None for value in entropies)
    threshold = float(np.quantile([float(value) for value in entropies if value is not None], 0.9))

    live_clear = [sample(random.Random(1000 + index), 0).prompt for index in range(80)]
    assert all(_entropy(prompt) < threshold for prompt in live_clear)

    rambling_draws = [
        sample(random.Random(2000 + index), 1, {VAGUE_RAMBLING: 1}) for index in range(40)
    ]
    assert {item.scenario for item in rambling_draws} == {VAGUE_RAMBLING}
    assert all(_entropy(item.prompt) > threshold for item in rambling_draws)

    loop_weights = dict.fromkeys(VAGUE_SCENARIOS, 0.0)
    loop_weights[VAGUE_CLARIFY_LOOP] = 1
    short = [sample(random.Random(3000 + index), 1, loop_weights).prompt for index in range(20)]
    assert all(_entropy(prompt) < threshold for prompt in short)


def test_score_polling_backs_off_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_latest(api_url: str, trace_id: str) -> dict[str, object] | None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RateLimited(0.01)
        return {"status": "complete", "root_cause": "compliant"}

    monkeypatch.setattr("drift_demo.report._latest_score", fake_latest)
    monkeypatch.setattr("drift_demo.report.POLL_GAP_SECONDS", 0)
    rows = collect_scores(
        "http://localhost:18000",
        [{"trace_id": "ab" * 16, "scenario": "clear"}],
        deadline=5,
    )
    assert calls["count"] == 2
    assert rows[0]["score"] == {"status": "complete", "root_cause": "compliant"}


def _sequence(seed: int):
    rng = random.Random(seed)
    return [sample(rng, 0.4) for _ in range(30)]


def _entropy(prompt: str) -> float:
    value = shannon_entropy(prompt)
    assert value is not None
    return value
