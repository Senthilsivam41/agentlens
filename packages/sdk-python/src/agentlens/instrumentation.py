"""Configure OTel export and optional framework instrumentation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from typing import Literal

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

FrameworkName = Literal["langgraph", "crewai", "generic"]


class InstrumentationError(RuntimeError):
    """Raised when Agent Lens instrumentation cannot be configured safely."""


@dataclass(frozen=True, slots=True)
class AgentLensConfig:
    framework: FrameworkName
    agent_name: str
    agent_version: str
    environment: str
    service_name: str
    otlp_endpoint: str
    insecure: bool = True
    baseline_ref: str | None = None

    @classmethod
    def from_env(
        cls,
        *,
        framework: FrameworkName,
        agent_name: str,
        agent_version: str,
        environment: str | None = None,
        service_name: str | None = None,
        otlp_endpoint: str | None = None,
        insecure: bool | None = None,
        baseline_ref: str | None = None,
    ) -> AgentLensConfig:
        resolved_endpoint = _required(
            "otlp_endpoint",
            otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4317",
        )
        resolved_insecure = (
            insecure
            if insecure is not None
            else os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
        )
        resolved_baseline = baseline_ref or os.getenv("AGENTLENS_BASELINE_REF") or None
        if resolved_baseline is not None:
            resolved_baseline = _required("baseline_ref", resolved_baseline)
        return cls(
            framework=framework,
            agent_name=_required("agent_name", agent_name),
            agent_version=_required("agent_version", agent_version),
            environment=_required(
                "environment",
                environment or os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT") or "development",
            ),
            service_name=_required(
                "service_name", service_name or os.getenv("OTEL_SERVICE_NAME") or agent_name
            ),
            otlp_endpoint=resolved_endpoint,
            insecure=resolved_insecure,
            baseline_ref=resolved_baseline,
        )


def _required(field: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InstrumentationError(f"{field} must not be empty")
    return cleaned


def instrument(
    *,
    framework: FrameworkName,
    agent_name: str,
    agent_version: str,
    environment: str | None = None,
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
    insecure: bool | None = None,
    baseline_ref: str | None = None,
) -> TracerProvider:
    """Configure an OTel provider and activate a supported framework instrumentor."""
    config = AgentLensConfig.from_env(
        framework=framework,
        agent_name=agent_name,
        agent_version=agent_version,
        environment=environment,
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        insecure=insecure,
        baseline_ref=baseline_ref,
    )
    attributes = {
        "service.name": config.service_name,
        "deployment.environment.name": config.environment,
        "agentlens.agent.name": config.agent_name,
        "agentlens.agent.version": config.agent_version,
        "agentlens.framework": config.framework,
    }
    if config.baseline_ref:
        attributes["agentlens.baseline_ref"] = config.baseline_ref
    resource = Resource.create(attributes)
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint, insecure=config.insecure)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _activate_framework(config.framework, provider)
    return provider


def _activate_framework(framework: FrameworkName, provider: TracerProvider) -> None:
    if framework == "generic":
        return
    modules = {
        "langgraph": (
            "openinference.instrumentation.langchain",
            "LangChainInstrumentor",
            "agentlens[langgraph]",
        ),
        "crewai": (
            "openinference.instrumentation.crewai",
            "CrewAIInstrumentor",
            "agentlens[crewai]",
        ),
    }
    module_name, class_name, extra = modules[framework]
    try:
        instrumentor_type = getattr(import_module(module_name), class_name)
    except (ImportError, AttributeError) as exc:
        raise InstrumentationError(
            f"{framework} instrumentation is unavailable; install {extra}"
        ) from exc
    instrumentor_type().instrument(tracer_provider=provider)
