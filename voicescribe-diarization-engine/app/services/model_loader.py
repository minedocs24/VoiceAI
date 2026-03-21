"""Pyannote pipeline loader with HuggingFace token validation."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from structlog import get_logger

from app.core.config import settings
from app.core.gpu_state import loaded_model, model_lock, runtime_state
from app.core.metrics import GPU_VRAM_FREE_MB, GPU_VRAM_TOTAL_MB, MODEL_VRAM_USED_MB

logger = get_logger(__name__)

# HuggingFace token: tipicamente inizia con hf_ e ha lunghezza sufficiente
HF_TOKEN_MIN_LEN = 10
HF_TOKEN_PREFIX = "hf_"


def _validate_hf_token(token: str) -> bool:
    """Verifica che il token sia configurato e in formato valido (senza esporlo)."""
    if not token or not token.strip():
        return False
    t = token.strip()
    if len(t) < HF_TOKEN_MIN_LEN:
        return False
    if not t.startswith(HF_TOKEN_PREFIX):
        return False
    return True


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
    """Carica il modello Pyannote una sola volta. In caso di token invalido o errore rilancia."""
    global loaded_model

    if not _validate_hf_token(settings.huggingface_token):
        runtime_state.ready = False
        runtime_state.hf_token_valid = False
        runtime_state.last_error = (
            "HUGGINGFACE_TOKEN is required and must be a valid HuggingFace token (e.g. hf_...). "
            "See docs/HUGGINGFACE-SETUP.md to obtain and configure it."
        )
        logger.error("hf_token_invalid", message=runtime_state.last_error)
        raise RuntimeError(runtime_state.last_error)

    runtime_state.hf_token_valid = True

    with model_lock:
        if loaded_model is not None and not force:
            return loaded_model

        start = time.perf_counter()
        free_before, total_before = _get_cuda_info_mb()

        try:
            from pyannote.audio import Pipeline
            import torch

            os.environ["HF_TOKEN"] = settings.huggingface_token
            cache_dir = Path(settings.hf_home).expanduser().resolve()
            cache_dir.mkdir(parents=True, exist_ok=True)

            loaded_model = Pipeline.from_pretrained(
                settings.pyannote_model,
                use_auth_token=settings.huggingface_token,
                cache_dir=str(cache_dir),
            )
            if torch.cuda.is_available():
                loaded_model = loaded_model.to(torch.device("cuda"))

            free_after, total_after = _get_cuda_info_mb()
            model_vram = max(free_before - free_after, 0.0)
            elapsed_s = time.perf_counter() - start

            runtime_state.model_name = settings.pyannote_model
            runtime_state.model_vram_used_mb = model_vram
            runtime_state.load_seconds = elapsed_s
            runtime_state.ready = True
            runtime_state.last_error = None

            logger.info(
                "model_loaded",
                model=settings.pyannote_model,
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
            msg = (
                "Failed to load Pyannote model. Check HUGGINGFACE_TOKEN and that you have "
                "accepted the model terms at https://huggingface.co/pyannote/speaker-diarization-3.1. "
                f"Details: {exc}"
            )
            raise RuntimeError(msg) from exc


def ensure_ready_or_exit() -> None:
    """Se il modello non è pronto (token invalido o load fallito), termina il processo con exit non-zero."""
    try:
        load_model_once()
    except RuntimeError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
