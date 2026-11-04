"""Seeded prompt catalog for the customer drift demo.

Clear prompts stay short so their Shannon entropy sits under the baseline's
90th percentile. Rambling prompts are long and made of unique tokens so they
clear that threshold. Loop and tool-failure prompts stay very short, because
those scenarios are meant to trip volatility and tool errors, not ambiguity.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final

CLEAR = "clear"
VAGUE_RAMBLING = "vague_rambling"
VAGUE_CLARIFY_LOOP = "vague_clarify_loop"
TOOL_FAILURE = "tool_failure"
AGENT_REGRESSION = "agent_regression"

VAGUE_SCENARIOS: Final[tuple[str, ...]] = (
    VAGUE_RAMBLING,
    VAGUE_CLARIFY_LOOP,
    TOOL_FAILURE,
)

EXPECTED_ROOT_CAUSE: Final[dict[str, str]] = {
    CLEAR: "compliant",
    VAGUE_RAMBLING: "user_prompt_ambiguity",
    VAGUE_CLARIFY_LOOP: "high_volatility",
    TOOL_FAILURE: "tool_runtime_failure",
    AGENT_REGRESSION: "agent_logic_failure",
}

INTENTS: Final[tuple[str, ...]] = (
    "order_status",
    "product_question",
    "refund",
    "account_change",
)

ORDER_IDS: Final[tuple[str, ...]] = ("A1001", "A1002", "A1003", "A1004", "B2208", "B2219")
SKUS: Final[tuple[str, ...]] = ("SKU-RED-1", "SKU-BLU-4", "SKU-GRN-9", "SKU-BLK-2")
EMAILS: Final[tuple[str, ...]] = (
    "ada@example.com",
    "grace@example.com",
    "lin@example.com",
    "noah@example.com",
)

# 6-8 unique tokens. These are the only clear prompts live traffic sends.
CONCISE_TEMPLATES: Final[dict[str, tuple[str, ...]]] = {
    "order_status": (
        "Where is order {order_id} shipping today?",
        "Track order {order_id} for {email}.",
        "Status of order {order_id} please.",
    ),
    "product_question": (
        "Is sku {sku} in stock now?",
        "Does sku {sku} ship tomorrow?",
        "Availability for sku {sku} please.",
    ),
    "refund": (
        "Refund order {order_id} to {email}.",
        "Return order {order_id} for sku {sku}.",
        "Issue refund for order {order_id}.",
    ),
    "account_change": (
        "Change account email to {email}.",
        "Update login email to {email}.",
        "Set account contact to {email}.",
    ),
}

# Baseline-only prompts. Twenty-plus unique tokens lift the entropy percentile
# above every concise prompt without changing the agent's tool path.
_LONG_PREFIX: Final[tuple[str, ...]] = (
    "please",
    "confirm",
    "complete",
    "outbound",
    "delivery",
    "timeline",
    "including",
    "warehouse",
    "departure",
    "carrier",
    "handoff",
    "customs",
    "scan",
    "estimated",
    "customer",
    "arrival",
    "window",
    "today",
    "priority",
    "handling",
)

_RAMBLING_BANK: Final[tuple[str, ...]] = (
    "hey",
    "maybe",
    "somehow",
    "whatever",
    "earlier",
    "before",
    "thing",
    "stuff",
    "kinda",
    "sorta",
    "around",
    "someone",
    "somewhere",
    "unclear",
    "vague",
    "muddled",
    "rambling",
    "aside",
    "anyway",
    "perhaps",
    "possibly",
    "roughly",
    "vaguely",
    "loosely",
    "casually",
    "briefly",
    "mentioned",
    "forgotten",
    "misplaced",
    "unspecified",
    "ambiguous",
    "generic",
    "random",
    "unrelated",
    "tangential",
    "wandering",
    "hedging",
    "guessing",
    "assuming",
    "wondering",
    "hoping",
    "needing",
    "wanting",
    "asking",
    "checking",
    "looking",
    "poking",
    "nudging",
    "fixing",
    "handling",
)

_LOOP_PROMPTS: Final[tuple[str, ...]] = ("fix it", "help", "the thing", "do that")
_ACCOUNT_PROMPTS: Final[tuple[str, ...]] = (
    "update the account",
    "change that account",
    "fix the account",
    "account please",
)


@dataclass(frozen=True, slots=True)
class PromptSample:
    scenario: str
    intent: str
    prompt: str


def concise_prompt(rng: random.Random, intent: str) -> str:
    """Return a short, fully specified prompt for one intent."""

    template = rng.choice(CONCISE_TEMPLATES[intent])
    return template.format(
        order_id=rng.choice(ORDER_IDS),
        sku=rng.choice(SKUS),
        email=rng.choice(EMAILS),
    )


def baseline_prompt(rng: random.Random) -> tuple[str, str]:
    """Return one baseline example. One in five is intentionally long."""

    intent = rng.choice(INTENTS)
    if rng.random() < 0.2:
        return intent, _long_prompt(rng, intent)
    return intent, concise_prompt(rng, intent)


def sample(
    rng: random.Random,
    vague_ratio: float = 0.4,
    weights: dict[str, float] | None = None,
) -> PromptSample:
    """Draw one labeled prompt. `vague_ratio` is the chance of a vague scenario."""

    if not 0 <= vague_ratio <= 1:
        raise ValueError("vague_ratio must be between 0 and 1")
    scenario = _weighted_scenario(rng, weights) if rng.random() < vague_ratio else CLEAR
    intent = rng.choice(INTENTS)
    return PromptSample(scenario=scenario, intent=intent, prompt=prompt_for(rng, scenario, intent))


def prompt_for(rng: random.Random, scenario: str, intent: str) -> str:
    if scenario in {CLEAR, AGENT_REGRESSION}:
        return concise_prompt(rng, intent)
    if scenario == VAGUE_RAMBLING:
        return _rambling_prompt(rng)
    if scenario == VAGUE_CLARIFY_LOOP:
        return rng.choice(_LOOP_PROMPTS)
    if scenario == TOOL_FAILURE:
        return rng.choice(_ACCOUNT_PROMPTS)
    raise ValueError(f"unknown scenario: {scenario}")


def _long_prompt(rng: random.Random, intent: str) -> str:
    order_id = rng.choice(ORDER_IDS)
    sku = rng.choice(SKUS)
    email = rng.choice(EMAILS)
    subject = {
        "order_status": f"order {order_id}",
        "product_question": f"sku {sku}",
        "refund": f"refund {order_id}",
        "account_change": f"account {email}",
    }[intent]
    return f"{' '.join(_LONG_PREFIX)} for {subject}"


def _rambling_prompt(rng: random.Random) -> str:
    words = rng.sample(_RAMBLING_BANK, 42)
    return " ".join(words)


def _weighted_scenario(rng: random.Random, weights: dict[str, float] | None) -> str:
    selected = weights or dict.fromkeys(VAGUE_SCENARIOS, 1.0)
    names = [name for name in VAGUE_SCENARIOS if selected.get(name, 0) > 0]
    if not names:
        raise ValueError("vague scenario weights must include a positive weight")
    return rng.choices(names, weights=[selected[name] for name in names], k=1)[0]
