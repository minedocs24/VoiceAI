"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

JOBS_BY_STATUS = Gauge(
    "orchestrator_jobs_by_status",
    "Number of jobs per status",
    ["status"],
)
JOBS_COMPLETED_TOTAL = Counter(
    "orchestrator_jobs_completed_total",
    "Total jobs completed",
)
STAGE_LATENCY_SECONDS = Histogram(
    "orchestrator_stage_latency_seconds",
    "Latency per pipeline stage",
    ["stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
CIRCUIT_BREAKER_OPEN = Gauge(
    "orchestrator_circuit_breaker_open",
    "Circuit breaker open (1=open)",
    ["service"],
)
RETRY_TOTAL = Counter(
    "orchestrator_retry_total",
    "Retries by stage and error type",
    ["stage", "error_type"],
)
