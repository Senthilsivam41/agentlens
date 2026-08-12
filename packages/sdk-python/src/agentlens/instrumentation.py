"""Configure OTel export and optional framework instrumentation (ADR-008)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from . import attributes as attrs
from .adapters import activate
from .errors import InstrumentationError

FrameworkName = Literal["langgraph", "langchain", "crewai", "adk", "generic"]


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
    agent_id: str | None = None

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
        agent_id: str | None = None,
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
        resolved_agent_id = agent_id or os.getenv("AGENTLENS_AGENT_ID") or agent_name
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
            agent_id=_required("agent_id", resolved_agent_id),
        )


def _required(field: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InstrumentationError(f"{field} must not be empty")
    return cleaned


def init(
    *,
    framework: FrameworkName = "generic",
    agent_name: str,
    agent_version: str,
    environment: str | None = None,
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
    insecure: bool | None = None,
    baseline_ref: str | None = None,
    agent_id: str | None = None,
) -> TracerProvider:
    """Initialize AgentLens OTel export and activate a framework adapter.

    Thin wrapper over the OpenTelemetry SDK. Correctly instrumented OTLP clients
    may skip this helper entirely (ADR-003 / ADR-008 Tier 2).
    """
    config = AgentLensConfig.from_env(
        framework=framework,
        agent_name=agent_name,
        agent_version=agent_version,
        environment=environment,
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        insecure=insecure,
        baseline_ref=baseline_ref,
        agent_id=agent_id,
    )
    resource_attrs = {
        "service.name": config.service_name,
        "deployment.environment.name": config.environment,
        attrs.AGENT_NAME: config.agent_name,
        attrs.AGENT_VERSION: config.agent_version,
        attrs.AGENT_ID: config.agent_id or config.agent_name,
        attrs.FRAMEWORK: config.framework,
    }
    if config.baseline_ref:
        resource_attrs[attrs.BASELINE_REF] = config.baseline_ref
    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint, insecure=config.insecure)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    activate(config.framework, provider)
    return provider


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
    agent_id: str | None = None,
) -> TracerProvider:
    """Backward-compatible alias for :func:`init`."""
    return init(
        framework=framework,
        agent_name=agent_name,
        agent_version=agent_version,
        environment=environment,
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        insecure=insecure,
        baseline_ref=baseline_ref,
        agent_id=agent_id,
    )
