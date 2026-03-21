# syntax=docker/dockerfile:1.4
# Multi-stage: builder installs deps (incl. python-docx), runtime copies app.

FROM python:3.11-slim as builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY pyproject.toml README.md openapi.yaml run.py ./
COPY app ./app
COPY config ./config

RUN mkdir -p /data/output /mnt/ramdisk

EXPOSE 8007
CMD ["python3", "run.py"]
