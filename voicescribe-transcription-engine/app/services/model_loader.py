"""Whisper model loader singleton."""

from __future__ import annotations

import time

from structlog import get_logger

from app.core.config import settings
from app.core.gpu_state import loaded_model, model_lock, runtime_state
from app.core.metrics import GPU_VRAM_FREE_MB, GPU_VRAM_TOTAL_MB, MODEL_VRAM_USED_MB

logger = get_logger(__name__)


def _get_cuda_info_mb() -> tuple[float, float]:
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0, 0.0
        free, total = torch.cuda.mem_get_info()
        free_mb = free / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        GPU_VRAM_FREE_MB.set(free_mb)
        GPU_VRAM_TOTAL_MB.set(total_mb)
        MODEL_VRAM_USED_MB.set(max(total_mb - free_mb, 0.0))
        return free_mb, total_mb
    except Exception:
        return 0.0, 0.0


def load_model_once(force: bool = False):
    global loaded_model

    with model_lock:
        if loaded_model is not None and not force:
            return loaded_model

        start = time.perf_counter()
        free_before, total_before = _get_cuda_info_mb()

        try:
            from faster_whisper import WhisperModel
            import torch

            if settings.whisper_device == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("CUDA is requested but not available")

            loaded_model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                download_root=settings.whisper_cache_dir,
            )

            free_after, total_after = _get_cuda_info_mb()
            model_vram = max(free_before - free_after, 0.0)
            elapsed_s = time.perf_counter() - start

            runtime_state.model_name = settings.whisper_model
            runtime_state.compute_type = settings.whisper_compute_type
            runtime_state.cuda_version = getattr(torch.version, "cuda", "n/a") if settings.whisper_device == "cuda" else "cpu"
            runtime_state.model_vram_used_mb = model_vram
            runtime_state.ready = True
            runtime_state.last_error = None

            logger.info(
                "model_loaded",
                model=settings.whisper_model,
                compute_type=settings.whisper_compute_type,
                vram_used_mb=model_vram,
                vram_free_mb=free_after,
                vram_total_mb=total_after,
                load_seconds=elapsed_s,
            )
            return loaded_model
        except Exception as exc:
            runtime_state.ready = False
            runtime_state.last_error = str(exc)
            logger.error("model_load_failed", error=str(exc))
            raise
