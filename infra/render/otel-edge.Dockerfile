# Edge OTel collector for Render (public OTLP ingest). Bakes the Render edge
# config into the image so no volume mount is required.
#
# Build context must be the repository root (dockerContext: .).
FROM otel/opentelemetry-collector-contrib:0.157.0

COPY infra/render/edge-config.yaml /etc/agentlens/edge.yaml

CMD ["--config", "/etc/agentlens/edge.yaml"]
