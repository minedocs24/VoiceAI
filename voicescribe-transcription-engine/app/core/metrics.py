"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

INFERENCE_DURATION_SECONDS = Histogram(
    "transcription_inference_duration_seconds",
    "Whisper inference latency in seconds",
    buckets=[0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60],
)
RTF_HISTOGRAM = Histogram(
    "transcription_rtf",
    "Real Time Factor values",
    buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0],
)
INFERENCE_SUCCESS_TOTAL = Counter(
    "transcription_inference_success_total",
    "Inference completed successfully",
)
INFERENCE_FAILURE_TOTAL = Counter(
    "transcription_inference_failure_total",
    "Inference failures by error type",
    ["error_type"],
)
AUTO_SPLIT_TOTAL = Counter(
    "transcription_auto_split_total",
    "Jobs processed using auto-split",
)
MODEL_VRAM_USED_MB = Gauge(
    "transcription_model_vram_used_mb",
    "VRAM used by the loaded model in MB",
)
GPU_VRAM_FREE_MB = Gauge(
    "transcription_gpu_vram_free_mb",
    "Current free VRAM in MB",
)
GPU_VRAM_TOTAL_MB = Gauge(
    "transcription_gpu_vram_total_mb",
    "Current total VRAM in MB",
)
