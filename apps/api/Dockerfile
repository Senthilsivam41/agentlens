FROM python:3.12.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN addgroup --system agentlens && adduser --system --ingroup agentlens agentlens

COPY packages/contracts /build/packages/contracts
COPY apps/api /build/apps/api
RUN pip install --no-cache-dir /build/packages/contracts /build/apps/api

USER agentlens
EXPOSE 8000
CMD ["uvicorn", "agentlens_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

