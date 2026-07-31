"""Emit one OpenInference-compatible trace through the local Agent Lens edge."""

from __future__ import annotations

import argparse

from agentlens import instrument
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4317")
    args = parser.parse_args()
    provider = instrument(
        framework="generic",
        agent_name="pilot-smoke-agent",
        agent_version="1.0.0",
        environment="development",
        otlp_endpoint=args.endpoint,
        insecure=True,
    )
    tracer = trace.get_tracer("agentlens.smoke")
    with tracer.start_as_current_span("agent.run") as root:
        root.set_attribute("input.value", "Summarize the current order status")
        root.set_attribute("output.value", "The order is ready for shipment")
        root.set_attribute("gen_ai.usage.input_tokens", 7)
        root.set_attribute("gen_ai.usage.output_tokens", 8)
        with tracer.start_as_current_span("lookup-order") as child:
            child.set_attribute("tool.name", "order_lookup")
            child.set_status(Status(StatusCode.OK))
        root.set_status(Status(StatusCode.OK))
        trace_id = f"{root.get_span_context().trace_id:032x}"
    provider.force_flush(timeout_millis=10_000)
    provider.shutdown()
    print(trace_id)


if __name__ == "__main__":
    main()
