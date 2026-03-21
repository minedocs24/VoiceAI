"""API routes for transcription service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.celery_app import celery_app
from app.core.config import settings
from app.core.gpu_state import runtime_state
from app.core.security import validate_job_id, validate_tenant_id, verify_internal_token
from app.models.schemas import AsyncTranscribeResponse, ModelsResponse, ModelInfo, TaskStatusResponse, TranscribeRequest
from app.services.model_loader import load_model_once
from app.services.transcription import transcribe_audio
from app.tasks import transcribe_task

router = APIRouter(tags=["transcription"])


@router.post("/transcribe")
async def transcribe_sync(
    body: TranscribeRequest,
    _: Annotated[None, Depends(verify_internal_token)] = None,
):
    job_id = validate_job_id(body.job_id)
    if body.tenant_id:
        validate_tenant_id(body.tenant_id)

    model = load_model_once()
    result = transcribe_audio(job_id=job_id, audio_path=body.input_path, model=model, beam_size=body.beam_size)
    return result


@router.post("/transcribe/async", response_model=AsyncTranscribeResponse)
async def transcribe_async(
    body: TranscribeRequest,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> AsyncTranscribeResponse:
    job_id = validate_job_id(body.job_id)
    tenant_id = validate_tenant_id(body.tenant_id or "standalone")

    result = transcribe_task.apply_async(
        args=[job_id, tenant_id, body.input_path],
        queue=settings.celery_queue_name,
    )
    return AsyncTranscribeResponse(task_id=result.id, job_id=job_id)


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> TaskStatusResponse:
    result = celery_app.AsyncResult(task_id)

    status = "pending"
    payload = None
    err = None
    if result.ready():
        if result.successful():
            status = "success"
            payload = result.result
        else:
            status = "failure"
            err = str(result.result) if result.result else str(result.info)

    return TaskStatusResponse(task_id=task_id, status=status, result=payload, error=err)


@router.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    active = ModelInfo(
        name=runtime_state.model_name or settings.whisper_model,
        compute_type=runtime_state.compute_type or settings.whisper_compute_type,
        loaded=runtime_state.ready,
    )
    return ModelsResponse(active_model=active, supported_models=["tiny", "base", "small", "medium", "large-v3"])
