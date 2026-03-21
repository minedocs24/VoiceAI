"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

PREPROCESS_TASKS_TOTAL = Counter(
    "preprocess_tasks_total",
    "Total preprocess tasks",
    ["status"],
)
PREPROCESS_DURATION_SECONDS = Histogram(
    "preprocess_duration_seconds",
    "Preprocessing duration in seconds",
    buckets=[1, 2, 5, 10, 30, 60, 120],
)
QUOTA_CHECK_FAILURES_TOTAL = Counter(
    "quota_check_failures_total",
    "Quota check failures",
)
CALLBACK_RETRIES_TOTAL = Counter(
    "callback_retries_total",
    "Callback notification retries",
)
