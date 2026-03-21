"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

EXPORT_DURATION_SECONDS = Histogram(
    "export_duration_seconds",
    "Export processing latency in seconds",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)
EXPORT_SUCCESS_TOTAL = Counter(
    "export_success_total",
    "Exports completed successfully",
)
EXPORT_FAILURE_TOTAL = Counter(
    "export_failure_total",
    "Export failures by error type",
    ["error_type"],
)
CLEANUP_FILES_DELETED_TOTAL = Counter(
    "export_cleanup_files_deleted_total",
    "Files deleted by cleanup operations",
)
CLEANUP_SPACE_FREED_BYTES = Counter(
    "export_cleanup_space_freed_bytes",
    "Bytes freed by cleanup operations",
)
