"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

DIARIZATION_DURATION_SECONDS = Histogram(
    "diarization_inference_duration_seconds",
    "Diarization inference latency in seconds",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)
DIARIZATION_SUCCESS_TOTAL = Counter(
    "diarization_inference_success_total",
    "Diarization completed successfully",
)
DIARIZATION_FAILURE_TOTAL = Counter(
    "diarization_inference_failure_total",
    "Diarization failures by error type",
    ["error_type"],
)
MODEL_VRAM_USED_MB = Gauge(
    "diarization_model_vram_used_mb",
    "VRAM used by the loaded model in MB",
)
GPU_VRAM_FREE_MB = Gauge(
    "diarization_gpu_vram_free_mb",
    "Current free VRAM in MB",
)
GPU_VRAM_TOTAL_MB = Gauge(
    "diarization_gpu_vram_total_mb",
    "Current total VRAM in MB",
)
