FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings celery redis structlog pyyaml prometheus-client httpx

COPY app/ app/
COPY config/ config/
COPY openapi.yaml .
COPY run.py .

USER appuser

EXPOSE 8003
VOLUME ["/mnt/ramdisk"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

CMD ["python", "run.py"]
