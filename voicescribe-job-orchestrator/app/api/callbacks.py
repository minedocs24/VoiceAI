"""Callback handlers from downstream services."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from structlog import get_logger

from app.core.config import settings
from app.core.database import get_job_for_update, transition_job
from app.core.redis_client import publish_job_status
from app.core.security import verify_internal_token
from app.models.schemas import (
    DiarizationCompleteRequest,
    ExportCompleteRequest,
    PreprocessingCompleteRequest,
    TranscriptionCompleteRequest,
)
from app.services.http_client import call_svc02_delete_files, call_svc08_cleanup
from app.services.state_machine import get_next_stage_for_tier
from app.celery_app import send_diarize_task, send_export_task, send_transcribe_task

logger = get_logger(__name__)

router = APIRouter(prefix="/callbacks", tags=["callbacks"])


def _do_rollback(job_id: str) -> None:
    """Best-effort rollback: SVC-02 delete files, SVC-08 cleanup."""
    call_svc02_delete_files(job_id)
    call_svc08_cleanup(job_id)


async def _transition_and_trigger(
    job_id: UUID,
    from_status: str,
    to_status: str,
    **kwargs,
) -> bool:
    ok = await transition_job(job_id, from_status, to_status, **kwargs)
    if not ok:
        logger.warning("invalid_transition", job_id=str(job_id), from_status=from_status, to_status=to_status)
        return False
    return True


@router.post("/preprocessing-complete")
async def preprocessing_complete(
    body: PreprocessingCompleteRequest,
    _: None = Depends(verify_internal_token),
):
    """Callback from SVC-04 when preprocessing is done."""
    job_id = UUID(body.job_id)
    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "PREPROCESSING":
        raise HTTPException(status_code=422, detail=f"Invalid state: {job['status']}")

    if body.success:
        ok = await _transition_and_trigger(
            job_id,
            "PREPROCESSING",
            "TRANSCRIBING",
            ramdisk_path=body.ramdisk_path,
        )
        if ok:
            try:
                send_transcribe_task(
                    str(job_id),
                    body.tenant_id,
                    job["tier_at_creation"],
                    body.ramdisk_path or "",
                )
            except Exception as e:
                logger.error("send_transcribe_failed", job_id=str(job_id), error=str(e))
                await transition_job(job_id, "TRANSCRIBING", "FAILED", error_code="dispatch_error", error_message=str(e))
                _do_rollback(str(job_id))
    else:
        await _transition_and_trigger(
            job_id,
            "PREPROCESSING",
            "FAILED",
            error_code=body.error_code or "preprocess_failed",
            error_message=body.error_message,
        )
        _do_rollback(str(job_id))

    return {"status": "ok"}


@router.post("/transcription-complete")
async def transcription_complete(
    body: TranscriptionCompleteRequest,
    _: None = Depends(verify_internal_token),
):
    """Callback from SVC-06 when transcription is done."""
    job_id = UUID(body.job_id)
    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "TRANSCRIBING":
        raise HTTPException(status_code=422, detail=f"Invalid state: {job['status']}")

    if body.success:
        next_stage = get_next_stage_for_tier("TRANSCRIBING", job["tier_at_creation"])
        if next_stage == "DIARIZING":
            ok = await _transition_and_trigger(
                job_id,
                "TRANSCRIBING",
                "DIARIZING",
                transcription_raw=body.transcription_raw,
                gpu_inference_ms=body.gpu_inference_ms,
            )
            if ok:
                try:
                    send_diarize_task(
                        str(job_id),
                        body.tenant_id,
                        job["tier_at_creation"],
                        job["ramdisk_path"] or "",
                        body.transcription_raw or {},
                    )
                except Exception as e:
                    logger.error("send_diarize_failed", job_id=str(job_id), error=str(e))
                    await transition_job(job_id, "DIARIZING", "FAILED", error_code="dispatch_error", error_message=str(e))
                    _do_rollback(str(job_id))
        else:
            ok = await _transition_and_trigger(
                job_id,
                "TRANSCRIBING",
                "EXPORTING",
                transcription_raw=body.transcription_raw,
                gpu_inference_ms=body.gpu_inference_ms,
            )
            if ok:
                try:
                    send_export_task(
                        str(job_id),
                        body.tenant_id,
                        job["tier_at_creation"],
                        job["ramdisk_path"] or "",
                        body.transcription_raw or {},
                        diarization_raw=None,
                    )
                except Exception as e:
                    logger.error("send_export_failed", job_id=str(job_id), error=str(e))
                    await transition_job(job_id, "EXPORTING", "FAILED", error_code="dispatch_error", error_message=str(e))
                    _do_rollback(str(job_id))
    else:
        await _transition_and_trigger(
            job_id,
            "TRANSCRIBING",
            "FAILED",
            error_code=body.error_code or "transcription_failed",
            error_message=body.error_message,
        )
        _do_rollback(str(job_id))

    return {"status": "ok"}


# Error codes per cui completare il job senza diarizzazione (fallback graceful)
DIARIZATION_SKIP_CODES = frozenset({
    "diarization_unavailable",
    "hf_token_invalid",
    "model_unavailable",
})


@router.post("/diarization-complete")
async def diarization_complete(
    body: DiarizationCompleteRequest,
    _: None = Depends(verify_internal_token),
):
    """Callback from SVC-07 when diarization is done."""
    job_id = UUID(body.job_id)
    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "DIARIZING":
        raise HTTPException(status_code=422, detail=f"Invalid state: {job['status']}")

    # Fallback graceful: SVC-07 non disponibile -> completare senza diarizzazione (EXPORTING, diarization_raw=None)
    skip_diarization = (
        (body.success and body.diarization_available is False)
        or (not body.success and (body.error_code or "") in DIARIZATION_SKIP_CODES)
    )

    if body.success and not skip_diarization:
        ok = await _transition_and_trigger(
            job_id,
            "DIARIZING",
            "EXPORTING",
            diarization_raw=body.diarization_raw,
        )
        if ok:
            try:
                send_export_task(
                    str(job_id),
                    body.tenant_id,
                    job["tier_at_creation"],
                    job["ramdisk_path"] or "",
                    job.get("transcription_raw") or {},
                    diarization_raw=body.diarization_raw,
                )
            except Exception as e:
                logger.error("send_export_failed", job_id=str(job_id), error=str(e))
                await transition_job(job_id, "EXPORTING", "FAILED", error_code="dispatch_error", error_message=str(e))
                _do_rollback(str(job_id))
    elif skip_diarization:
        ok = await _transition_and_trigger(
            job_id,
            "DIARIZING",
            "EXPORTING",
            diarization_raw=None,
        )
        if ok:
            try:
                send_export_task(
                    str(job_id),
                    body.tenant_id,
                    job["tier_at_creation"],
                    job["ramdisk_path"] or "",
                    job.get("transcription_raw") or {},
                    diarization_raw=None,
                )
            except Exception as e:
                logger.error("send_export_failed", job_id=str(job_id), error=str(e))
                await transition_job(job_id, "EXPORTING", "FAILED", error_code="dispatch_error", error_message=str(e))
                _do_rollback(str(job_id))
    else:
        await _transition_and_trigger(
            job_id,
            "DIARIZING",
            "FAILED",
            error_code=body.error_code or "diarization_failed",
            error_message=body.error_message,
        )
        _do_rollback(str(job_id))

    return {"status": "ok"}


@router.post("/export-complete")
async def export_complete(
    body: ExportCompleteRequest,
    _: None = Depends(verify_internal_token),
):
    """Callback from SVC-08 when export is done."""
    job_id = UUID(body.job_id)
    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "EXPORTING":
        raise HTTPException(status_code=422, detail=f"Invalid state: {job['status']}")

    if body.success:
        ok = await _transition_and_trigger(job_id, "EXPORTING", "DONE")
        if ok:
            publish_job_status(
                str(job_id),
                "DONE",
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "download_urls": body.download_urls or {},
                },
            )
    else:
        await _transition_and_trigger(
            job_id,
            "EXPORTING",
            "FAILED",
            error_code=body.error_code or "export_failed",
            error_message=body.error_message,
        )
        _do_rollback(str(job_id))

    return {"status": "ok"}
