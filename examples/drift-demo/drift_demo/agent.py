"""Simulated support agent whose behavior is chosen by demo scenario.

No model is called. Each scenario emits the span shape that Agent Lens scores:

- clear: canonical tool path and a stable answer
- vague_rambling: tools outside the baseline vocabulary and an off-topic answer
- vague_clarify_loop: the canonical path repeated until volatility crosses 4
- tool_failure: the account tool span ends in error
- agent_regression: a clear prompt, but the wrong tools and another intent's answer
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from agentlens_contracts import ExecutionFeatures, SpanStatus, TransientSpan
from agentlens_worker.features import extract_features
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import SecretStr

from .identity import AGENT_NAME, AGENT_VERSION, ENVIRONMENT, TENANT_ID
from .prompts import (
    AGENT_REGRESSION,
    CLEAR,
    TOOL_FAILURE,
    VAGUE_CLARIFY_LOOP,
    VAGUE_RAMBLING,
)

CANONICAL_TOOLS: dict[str, tuple[str, ...]] = {
    "order_status": ("order_lookup",),
    "product_question": ("kb_search",),
    "refund": ("order_lookup", "refund_issue"),
    "account_change": ("account_update",),
}

CANONICAL_OUTPUT: dict[str, str] = {
    "order_status": "Order is in transit and arrives tomorrow.",
    "product_question": "The product is in stock and ships in two days.",
    "refund": "Refund has been issued to the original payment method.",
    "account_change": "Account email has been updated successfully.",
}

WANDER_TOOLS: tuple[str, ...] = ("web_search", "guess_intent")
REGRESSION_TOOLS: tuple[str, ...] = ("escalate_human", "legacy_crm")
OFF_TOPIC_OUTPUT = (
    "Here is an unrelated note about the weather and office snacks instead of an answer."
)
LOOP_TOOL_SPANS = 9
PROMPT_TOKENS = 12
COMPLETION_TOKENS = 16

_OTHER_INTENT = {
    "order_status": "refund",
    "product_question": "account_change",
    "refund": "product_question",
    "account_change": "order_status",
}


@dataclass(frozen=True, slots=True)
class SpanSpec:
    name: str
    tool_name: str | None = None
    retry_count: int = 0
    error: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    input_text: str | None = None
    output_text: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    scenario: str
    intent: str
    prompt: str
    output: str
    spans: tuple[SpanSpec, ...]

    @property
    def tool_path(self) -> list[str]:
        return [span.tool_name for span in self.spans if span.tool_name]


class SupportAgent:
    """Deterministic support policy used by the demo."""

    def plan(self, prompt: str, scenario: str, intent: str) -> ExecutionPlan:
        tools, output, failed = _behavior(scenario, intent)
        spans: list[SpanSpec] = [
            SpanSpec(
                name="agent.run",
                prompt_tokens=PROMPT_TOKENS,
                completion_tokens=COMPLETION_TOKENS,
                input_text=prompt,
                output_text=output,
            )
        ]
        for tool in tools:
            spans.append(
                SpanSpec(
                    name=tool,
                    tool_name=tool,
                    error=failed,
                )
            )
        return ExecutionPlan(
            scenario=scenario,
            intent=intent,
            prompt=prompt,
            output=output,
            spans=tuple(spans),
        )

    def emit(self, tracer: trace.Tracer, plan: ExecutionPlan) -> str:
        """Emit the plan as one OpenInference-compatible trace. Returns the trace id."""

        with tracer.start_as_current_span("agent.run") as root:
            root.set_attribute("input.value", plan.prompt)
            root.set_attribute("output.value", plan.output)
            root.set_attribute("gen_ai.usage.input_tokens", PROMPT_TOKENS)
            root.set_attribute("gen_ai.usage.output_tokens", COMPLETION_TOKENS)
            root.set_attribute("agentlens.demo", True)
            root.set_attribute("agentlens.demo.scenario", plan.scenario)
            for spec in plan.spans:
                if spec.tool_name is None:
                    continue
                with tracer.start_as_current_span(spec.name) as child:
                    child.set_attribute("tool.name", spec.tool_name)
                    child.set_attribute("agentlens.demo", True)
                    if spec.retry_count:
                        child.set_attribute("agentlens.retry_count", spec.retry_count)
                    if spec.error:
                        child.set_status(Status(StatusCode.ERROR, "tool failed"))
                    else:
                        child.set_status(Status(StatusCode.OK))
            root.set_status(Status(StatusCode.OK))
            return f"{root.get_span_context().trace_id:032x}"


def features_for(plan: ExecutionPlan, *, hmac_key: bytes = b"drift-demo") -> ExecutionFeatures:
    """Score a dry-run plan with the same feature extractor the worker uses."""

    return extract_features(transient_spans(plan), hmac_key=hmac_key)


def transient_spans(plan: ExecutionPlan) -> list[TransientSpan]:
    started = datetime(2026, 9, 30, tzinfo=UTC)
    spans: list[TransientSpan] = []
    for index, spec in enumerate(plan.spans):
        spans.append(
            TransientSpan(
                event_id=f"drift-demo-event-{index:04d}",
                tenant_id=TENANT_ID,
                cluster_id="local-compose",
                environment=ENVIRONMENT,
                service_name=AGENT_NAME,
                agent_name=AGENT_NAME,
                agent_version=AGENT_VERSION,
                trace_id="d" * 32,
                span_id=f"{index:016x}",
                parent_span_id=None if index == 0 else "0000000000000000",
                span_name=spec.name,
                started_at=started + timedelta(milliseconds=index),
                ended_at=started + timedelta(milliseconds=index + 1),
                status=SpanStatus.ERROR if spec.error else SpanStatus.OK,
                tool_name=spec.tool_name,
                prompt_tokens=spec.prompt_tokens,
                completion_tokens=spec.completion_tokens,
                retry_count=spec.retry_count,
                input_text=SecretStr(spec.input_text) if spec.input_text else None,
                output_text=SecretStr(spec.output_text) if spec.output_text else None,
            )
        )
    return spans


def _loop_tools(canonical: tuple[str, ...]) -> tuple[str, ...]:
    """Repeat the canonical path until volatility crosses 4, keeping proportions."""

    repeats = 1
    while repeats * len(canonical) < LOOP_TOOL_SPANS:
        repeats += 1
    return canonical * repeats


def _behavior(scenario: str, intent: str) -> tuple[tuple[str, ...], str, bool]:
    canonical = CANONICAL_TOOLS[intent]
    if scenario == CLEAR:
        return canonical, CANONICAL_OUTPUT[intent], False
    if scenario == VAGUE_RAMBLING:
        return WANDER_TOOLS, OFF_TOPIC_OUTPUT, False
    if scenario == VAGUE_CLARIFY_LOOP:
        return _loop_tools(canonical), CANONICAL_OUTPUT[intent], False
    if scenario == TOOL_FAILURE:
        return (
            ("account_update",),
            "Could not update the account because the reference was missing.",
            True,
        )
    if scenario == AGENT_REGRESSION:
        other = _OTHER_INTENT[intent]
        return REGRESSION_TOOLS, CANONICAL_OUTPUT[other], False
    raise ValueError(f"unknown scenario: {scenario}")
