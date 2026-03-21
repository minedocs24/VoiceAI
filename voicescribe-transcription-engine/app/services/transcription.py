"""Core transcription service with auto-split and CUDA error handling."""

from __future__ import annotations

import os
import time
from typing import Any

from structlog import get_logger

from app.core.config import settings
from app.core.gpu_state import runtime_state, set_busy, update_last_rtf
from app.core.metrics import (
    AUTO_SPLIT_TOTAL,
    GPU_VRAM_FREE_MB,
    GPU_VRAM_TOTAL_MB,
    INFERENCE_DURATION_SECONDS,
    INFERENCE_FAILURE_TOTAL,
    INFERENCE_SUCCESS_TOTAL,
    MODEL_VRAM_USED_MB,
    RTF_HISTOGRAM,
)
from app.models.schemas import SegmentResult, TranscriptResult, WordResult
from app.services.audio_utils import extract_audio_chunk, get_audio_duration_seconds

logger = get_logger(__name__)


class CudaOOMError(RuntimeError):
    """Raised when CUDA runs out of memory."""


class CudaDeviceError(RuntimeError):
    """Raised for critical CUDA device errors."""


def _torch_cuda_info() -> tuple[float, float]:
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


def _segment_confidence(segment: Any) -> float:
    avg = 0.0
    probs = []
    for w in (getattr(segment, "words", None) or []):
        p = getattr(w, "probability", None)
        if isinstance(p, (float, int)):
            probs.append(float(p))
    if probs:
        avg = sum(probs) / len(probs)
    elif isinstance(getattr(segment, "avg_logprob", None), (float, int)):
        avg = min(max(float(getattr(segment, "avg_logprob")) + 1.0, 0.0), 1.0)
    return min(max(avg, 0.0), 1.0)


def _to_segment_result(raw_segment: Any, offset_s: float = 0.0) -> SegmentResult:
    words = []
    for w in (getattr(raw_segment, "words", None) or []):
        words.append(
            WordResult(
                word=str(getattr(w, "word", "")).strip(),
                start=float(getattr(w, "start", 0.0)) + offset_s,
                end=float(getattr(w, "end", 0.0)) + offset_s,
                probability=float(getattr(w, "probability", 0.0)),
            )
        )

    return SegmentResult(
        start=float(getattr(raw_segment, "start", 0.0)) + offset_s,
        end=float(getattr(raw_segment, "end", 0.0)) + offset_s,
        text=str(getattr(raw_segment, "text", "")).strip(),
        confidence=_segment_confidence(raw_segment),
        words=words,
    )


def build_transcript_result(job_id: str, language: str, duration: float, inference_ms: int, segments: list[SegmentResult]) -> TranscriptResult:
    rtf = (inference_ms / 1000.0) / duration if duration > 0 else 0.0
    return TranscriptResult(
        job_id=job_id,
        language=language,
        duration=duration,
        rtf=rtf,
        inference_ms=inference_ms,
        segments=segments,
    )


def deduplicate_overlap_segments(segments: list[SegmentResult]) -> list[SegmentResult]:
    if not segments:
        return []

    segments_sorted = sorted(segments, key=lambda s: (s.start, s.end))
    deduped: list[SegmentResult] = [segments_sorted[0]]

    for candidate in segments_sorted[1:]:
        last = deduped[-1]
        overlap = min(last.end, candidate.end) - max(last.start, candidate.start)
        if overlap > 0 and (candidate.text == last.text or overlap >= settings.auto_split_stride_length_s * 0.5):
            if candidate.confidence > last.confidence:
                deduped[-1] = candidate
        else:
            deduped.append(candidate)

    return deduped


def _run_inference(model: Any, audio_path: str, beam_size: int) -> tuple[list[SegmentResult], str]:
    try:
        segments, info = model.transcribe(
            audio_path,
            beam_size=beam_size,
            vad_filter=settings.whisper_vad_filter,
            word_timestamps=settings.word_timestamps,
            condition_on_previous_text=settings.condition_on_previous_text,
            temperature=settings.temperature,
        )
        language = str(getattr(info, "language", "unknown"))
        converted = [_to_segment_result(seg) for seg in segments]
        return converted, language
    except Exception as exc:
        text = str(exc).lower()
        if "out of memory" in text or "cuda oom" in text:
            raise CudaOOMError(str(exc)) from exc
        if "cuda" in text and ("device" in text or "driver" in text):
            raise CudaDeviceError(str(exc)) from exc
        raise


def _run_inference_with_cuda_recovery(model: Any, audio_path: str, beam_size: int) -> tuple[list[SegmentResult], str]:
    try:
        return _run_inference(model, audio_path, beam_size)
    except CudaOOMError as first_exc:
        INFERENCE_FAILURE_TOTAL.labels(error_type="cuda_oom_retry").inc()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        time.sleep(2)
        fallback_beam = max(1, beam_size - 2)
        try:
            return _run_inference(model, audio_path, fallback_beam)
        except Exception as second_exc:
            INFERENCE_FAILURE_TOTAL.labels(error_type="cuda_oom_final").inc()
            raise CudaOOMError(f"CUDA OOM after retry: {second_exc}") from first_exc


def _generate_chunk_windows(total_duration_s: float) -> list[tuple[float, float]]:
    chunk = settings.auto_split_chunk_length_s
    stride = settings.auto_split_stride_length_s
    step = max(chunk - stride, 1)

    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < total_duration_s:
        dur = min(chunk, total_duration_s - start)
        windows.append((start, dur))
        if start + dur >= total_duration_s:
            break
        start += step
    return windows


def transcribe_audio(job_id: str, audio_path: str, model: Any, beam_size: int | None = None) -> TranscriptResult:
    beam = beam_size or settings.whisper_beam_size
    audio_duration = get_audio_duration_seconds(audio_path)
    start_ts = time.perf_counter()

    free_before_mb, total_before_mb = _torch_cuda_info()
    set_busy(True)

    try:
        all_segments: list[SegmentResult] = []
        language = "unknown"

        if audio_duration > settings.auto_split_threshold_s:
            AUTO_SPLIT_TOTAL.inc()
            windows = _generate_chunk_windows(audio_duration)
            for offset_s, chunk_duration in windows:
                chunk_path = extract_audio_chunk(audio_path, offset_s, chunk_duration)
                chunk_segments, chunk_lang = _run_inference_with_cuda_recovery(model, chunk_path, beam)
                if language == "unknown":
                    language = chunk_lang
                for segment in chunk_segments:
                    shifted_words = [
                        WordResult(
                            word=w.word,
                            start=w.start + offset_s,
                            end=w.end + offset_s,
                            probability=w.probability,
                        )
                        for w in segment.words
                    ]
                    all_segments.append(
                        SegmentResult(
                            start=segment.start + offset_s,
                            end=segment.end + offset_s,
                            text=segment.text,
                            confidence=segment.confidence,
                            words=shifted_words,
                        )
                    )
        else:
            segments, language = _run_inference_with_cuda_recovery(model, audio_path, beam)
            all_segments.extend(segments)

        deduped = deduplicate_overlap_segments(all_segments)
        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        result = build_transcript_result(job_id, language, audio_duration, elapsed_ms, deduped)

        INFERENCE_DURATION_SECONDS.observe(elapsed_ms / 1000.0)
        RTF_HISTOGRAM.observe(result.rtf)
        INFERENCE_SUCCESS_TOTAL.inc()
        update_last_rtf(result.rtf)

        free_after_mb, total_after_mb = _torch_cuda_info()
        logger.info(
            "inference_completed",
            job_id=job_id,
            model=settings.whisper_model,
            compute_type=settings.whisper_compute_type,
            duration_seconds=elapsed_ms / 1000.0,
            audio_duration_seconds=audio_duration,
            rtf=result.rtf,
            language_detected=result.language,
            num_segments=len(result.segments),
            vram_used_mb_before=max(total_before_mb - free_before_mb, 0.0),
            vram_used_mb_after=max(total_after_mb - free_after_mb, 0.0),
        )
        return result
    except CudaDeviceError:
        INFERENCE_FAILURE_TOTAL.labels(error_type="cuda_device_error").inc()
        logger.error("cuda_device_error", job_id=job_id, alert="gpu_worker_unhealthy")
        raise
    except CudaOOMError:
        logger.error("cuda_oom_failure", job_id=job_id)
        raise
    except Exception:
        INFERENCE_FAILURE_TOTAL.labels(error_type="unknown_error").inc()
        raise
    finally:
        set_busy(False)
