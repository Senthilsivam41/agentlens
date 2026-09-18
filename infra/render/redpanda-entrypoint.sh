#!/usr/bin/env bash
# Render assigns each service a dynamic internal hostname, exposed to the service
# itself via $RENDER_DISCOVERY_SERVICE. Redpanda must advertise a broker address
# that clients can actually resolve, so we advertise that discovery hostname.
# Clients bootstrap at "<redpanda-internal-host>:9092" and are then handed this
# advertised address for subsequent connections.
#
# We invoke `rpk redpanda start` (the same wrapper the stock image uses) so the
# dev-friendly flags below are accepted.
set -euo pipefail

ADVERTISE_HOST="${RENDER_DISCOVERY_SERVICE:-0.0.0.0}"

exec /usr/bin/rpk redpanda start \
  --overprovisioned \
  --smp=1 \
  --memory=1G \
  --reserve-memory=0M \
  --node-id=0 \
  --check=false \
  --set redpanda.auto_create_topics_enabled=true \
  --kafka-addr "internal://0.0.0.0:9092" \
  --advertise-kafka-addr "internal://${ADVERTISE_HOST}:9092"
