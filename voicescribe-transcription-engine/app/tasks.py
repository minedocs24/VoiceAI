"""Celery tasks for transcription."""

from __future__ import annotations

from typing import Any

from celery.exceptions import Reject
from structlog import get_logger

from app.celery_app import celery_app
from app.models.schemas import CallbackPayload
from app.services.callback_client import send_transcription_callback
from app.services.model_loader import load_model_once
from app.services.transcription import CudaDeviceError, CudaOOMError, transcribe_audio

logger = get_logger(__name__)


@celery_app.task(bind=True, acks_late=True, reject_on_worker_lost=True)
def transcribe_task(self, job_id: str, tenant_id: str, ramdisk_path: str) -> dict[str, Any]:
    try:
        model = load_model_once()
        transcript = transcribe_audio(job_id=job_id, audio_path=ramdisk_path, model=model)
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=True,
            transcription_raw=transcript.model_dump(mode="json"),
            gpu_inference_ms=transcript.inference_ms,
        )
        send_transcription_callback(payload)
        return transcript.model_dump(mode="json")
    except CudaOOMError as exc:
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="cuda_oom",
            error_message=f"GPU memory exhausted. Reduce audio duration and retry. Details: {exc}",
        )
        send_transcription_callback(payload)
        raise Reject(reason=str(exc), requeue=False)
    except CudaDeviceError as exc:
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="cuda_device_error",
            error_message=f"Critical GPU device error: {exc}",
        )
        send_transcription_callback(payload)
        raise Reject(reason=str(exc), requeue=False)
    except Exception as exc:
        logger.exception("transcription_task_failed", job_id=job_id, error=str(exc))
        payload = CallbackPayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="transcription_failed",
            error_message=str(exc),
        )
        send_transcription_callback(payload)
        raise Reject(reason=str(exc), requeue=False)
