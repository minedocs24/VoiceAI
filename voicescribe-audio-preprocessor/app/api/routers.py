"""API routes for preprocessor."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from structlog import get_logger

from app.celery_app import celery_app
from app.core.config import settings
from app.core.security import validate_job_id, validate_tenant_id, verify_internal_token
from app.models.schemas import FormatsResponse, PreprocessRequest, PreprocessResponse, PreprocessStatusResponse
from app.tasks import preprocess_task

logger = get_logger(__name__)

router = APIRouter(tags=["preprocessor"])


@router.post("/preprocess", response_model=PreprocessResponse)
async def queue_preprocess(
    body: PreprocessRequest,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> PreprocessResponse:
    """Queue preprocessing task. Returns Celery task_id."""
    job_id = validate_job_id(body.job_id)
    tenant_id = validate_tenant_id(body.tenant_id)

    result = preprocess_task.apply_async(
        args=[job_id, tenant_id],
        kwargs={"input_path": body.input_path},
        queue=settings.celery_queue_name,
    )

    return PreprocessResponse(task_id=result.id, job_id=job_id)


@router.get("/preprocess/{task_id}/status", response_model=PreprocessStatusResponse)
async def get_preprocess_status(
    task_id: str,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> PreprocessStatusResponse:
    """Get Celery task status."""
    result = celery_app.AsyncResult(task_id)
    status = "pending"
    res = None
    err = None

    if result.ready():
        if result.successful():
            status = "success"
            res = result.result
        else:
            status = "failure"
            err = str(result.result) if result.result else str(result.info)

    return PreprocessStatusResponse(
        task_id=task_id,
        status=status,
        result=res,
        error=err,
    )


@router.get("/formats", response_model=FormatsResponse)
async def get_formats() -> FormatsResponse:
    """List supported audio formats."""
    return FormatsResponse(formats=settings.supported_formats)
