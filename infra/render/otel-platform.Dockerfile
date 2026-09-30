# Platform OTel collector for Render. Bakes the Render platform config into the
# image so no volume mount is required.
#
# Build context must be the repository root (dockerContext: .).
FROM otel/opentelemetry-collector-contrib:0.157.0

COPY infra/render/platform-config.yaml /etc/agentlens/platform.yaml

CMD ["--config", "/etc/agentlens/platform.yaml"]
