# Multi-stage build for Quota Manager Service
FROM python:3.11-slim as builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings redis asyncpg structlog pyyaml prometheus-client slowapi psycopg[binary]

FROM python:3.11-slim as runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings redis asyncpg structlog pyyaml prometheus-client slowapi psycopg[binary]

COPY app/ app/
COPY config/ config/
COPY openapi.yaml .
COPY run.py .

USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

# Graceful shutdown: uvicorn handles SIGTERM
CMD ["python", "run.py"]
