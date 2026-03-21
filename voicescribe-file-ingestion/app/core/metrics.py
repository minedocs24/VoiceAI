"""Prometheus metrics registry for ingestion service."""

from prometheus_client import Counter, Gauge, Histogram

UPLOAD_SUCCESS_TOTAL = Counter(
    "ingestion_upload_success_total",
    "Total successfully completed uploads",
)

UPLOAD_REJECTED_TOTAL = Counter(
    "ingestion_upload_rejected_total",
    "Total rejected uploads by reason",
    ["reason"],
)

UPLOAD_SIZE_BYTES = Histogram(
    "ingestion_upload_size_bytes",
    "Distribution of uploaded file sizes",
    buckets=(
        1024,
        1024 * 1024,
        10 * 1024 * 1024,
        100 * 1024 * 1024,
        1024 * 1024 * 1024,
        2 * 1024 * 1024 * 1024,
    ),
)

PROBE_DURATION_SECONDS = Histogram(
    "ingestion_probe_duration_seconds",
    "Duration of FFmpeg probe operations",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

DISK_SPACE_BYTES = Gauge(
    "ingestion_disk_space_bytes",
    "Disk space status in bytes",
    ["kind"],
)