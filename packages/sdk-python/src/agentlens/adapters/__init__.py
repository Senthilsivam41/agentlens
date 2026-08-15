"""Framework adapter activation (ADR-008 Tier 1)."""

from __future__ import annotations

import os
from importlib import import_module

from opentelemetry.sdk.trace import TracerProvider

from ..errors import InstrumentationError


def activate_langgraph(provider: TracerProvider) -> None:
    _openinference_instrument(
        module="openinference.instrumentation.langchain",
        class_name="LangChainInstrumentor",
        extra="agentlens[langgraph]",
        provider=provider,
    )


def activate_langchain(provider: TracerProvider) -> None:
    _openinference_instrument(
        module="openinference.instrumentation.langchain",
        class_name="LangChainInstrumentor",
        extra="agentlens[langchain]",
        provider=provider,
    )


def activate_crewai(provider: TracerProvider) -> None:
    _openinference_instrument(
        module="openinference.instrumentation.crewai",
        class_name="CrewAIInstrumentor",
        extra="agentlens[crewai]",
        provider=provider,
    )


def activate_adk(provider: TracerProvider) -> None:
    """Activate Google ADK tracing against the AgentLens TracerProvider.

    ADK (>=1.17 / 2.0) emits OTel GenAI spans when a global TracerProvider is set.
    This adapter keeps AgentLens as the provider owner, disables durable content
    capture by default (ADR-005), and verifies the ADK package is installed.
    """
    del provider  # already installed as the global provider by init()
    try:
        import google.adk  # noqa: F401
    except ImportError as exc:
        raise InstrumentationError(
            "adk instrumentation is unavailable; install agentlens[adk]"
        ) from exc
    # Prefer hash-only / no content in spans (ADR-005). Callers may override.
    os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT")


def activate_generic(_provider: TracerProvider) -> None:
    return None


ACTIVATORS = {
    "langgraph": activate_langgraph,
    "langchain": activate_langchain,
    "crewai": activate_crewai,
    "adk": activate_adk,
    "generic": activate_generic,
}


def activate(framework: str, provider: TracerProvider) -> None:
    try:
        ACTIVATORS[framework](provider)
    except KeyError as exc:
        raise InstrumentationError(f"unsupported framework: {framework}") from exc


def _openinference_instrument(
    *,
    module: str,
    class_name: str,
    extra: str,
    provider: TracerProvider,
) -> None:
    try:
        instrumentor_type = getattr(import_module(module), class_name)
    except (ImportError, AttributeError) as exc:
        raise InstrumentationError(
            f"framework instrumentation is unavailable; install {extra}"
        ) from exc
    instrumentor_type().instrument(tracer_provider=provider)
