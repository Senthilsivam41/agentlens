FROM python:3.12.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN addgroup --system agentlens && adduser --system --ingroup agentlens agentlens

COPY packages/contracts /build/packages/contracts
COPY services/stream-worker /build/services/stream-worker
RUN pip install --no-cache-dir /build/packages/contracts /build/services/stream-worker

USER agentlens
CMD ["agentlens-worker"]

