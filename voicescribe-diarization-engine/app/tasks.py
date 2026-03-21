"""Celery task per diarizzazione: consumato da coda gpu_tasks."""

from __future__ import annotations

from typing import Any

from celery.exceptions import Reject
from structlog import get_logger

from app.models.schemas import CallbackPayload
from app.services.callback_client import send_diarization_callback
from app.services.diarization_service import DiarizationUnavailableError, diarize_audio
from app.services.model_loader import load_model_once

from app.celery_app import celery_app

logger = get_logger(__name__)

@celery_app.task(bind=True, acks_late=True, reject_on_worker_lost=True)
def diarize_task(
    self,
    job_id: str,
    tenant_id: str,
    ramdisk_path: str,
    transcription_raw: dict | None = None,
) -> dict[str, Any]:
    """
    Task Celery: diarizza l'audio in ramdisk_path e merge con transcription_raw.
    In caso di modello non disponibile invia callback con success=True e diarization_available=False.
    """
    transcription_raw = transcription_raw or {}
    segments = transcription_raw.get("segments")
    duration = float(transcription_raw.get("duration", 0) or 0)
    language = str(transcription_raw.get("language", "unknown"))

    try:
        load_model_once()
    except RuntimeError as e:
        logger.warning("diarization_skipped_model_unavailable", job_id=job_id, error=str(e))
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=True,
            diarization_raw=None,
            diarization_available=False,
            error_code="diarization_unavailable",
            error_message=str(e),
        )
        send_diarization_callback(payload)
        return {"skipped": True, "reason": "model_unavailable"}

    try:
        result = diarize_audio(
            audio_path=ramdisk_path,
            segments=segments,
            job_id=job_id,
            language=language,
            duration=duration,
        )
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=True,
            diarization_raw=result,
            diarization_available=True,
        )
        send_diarization_callback(payload)
        return result
    except DiarizationUnavailableError as e:
        logger.warning("diarization_skipped_unavailable", job_id=job_id, error=str(e))
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=True,
            diarization_raw=None,
            diarization_available=False,
            error_code="diarization_unavailable",
            error_message=str(e),
        )
        send_diarization_callback(payload)
        return {"skipped": True, "reason": "diarization_unavailable"}
    except Exception as exc:
        logger.exception("diarization_task_failed", job_id=job_id, error=str(exc))
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            diarization_raw=None,
            error_code="diarization_failed",
            error_message=str(exc),
        )
        send_diarization_callback(payload)
        raise Reject(reason=str(exc), requeue=False)
