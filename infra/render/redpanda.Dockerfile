# Redpanda (Kafka API) for Render. We wrap the entrypoint so the advertised
# Kafka address uses Render's dynamic internal hostname ($RENDER_DISCOVERY_SERVICE)
# and enable auto topic creation (the local Compose stack pre-creates topics with
# a dedicated init container, which Blueprints don't model).
#
# Build context must be the repository root (dockerContext: .).
FROM redpandadata/redpanda:v25.2.9

USER root
COPY infra/render/redpanda-entrypoint.sh /usr/local/bin/redpanda-entrypoint.sh
RUN chmod +x /usr/local/bin/redpanda-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/redpanda-entrypoint.sh"]
