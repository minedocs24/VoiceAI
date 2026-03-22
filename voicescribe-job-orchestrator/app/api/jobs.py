"""Job management endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from structlog import get_logger

from app.core.database import create_job, get_job, transition_job
from app.core.security import verify_internal_token
from app.models.schemas import JobCreateRequest, JobCreateResponse, JobStatusResponse
from app.services.http_client import call_svc04_preprocess
from app.services.state_machine import validate_transition

logger = get_logger(__name__)

router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job_endpoint(
    body: JobCreateRequest,
    _: None = Depends(verify_internal_token),
) -> JobCreateResponse:
    """Create job in QUEUED, send task to SVC-04, transition to PREPROCESSING."""
    from app.core.database import get_job_for_update

    if not body.job_id:
        raise HTTPException(
            status_code=422,
            detail="job_id is required — job must be pre-created by api-gateway",
        )

    job_id = UUID(body.job_id)
    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "QUEUED":
        raise HTTPException(
            status_code=422,
            detail=f"Job already in state {job['status']}, cannot dispatch",
        )
    try:
        task_id = call_svc04_preprocess(str(job_id), body.tenant_id, input_path=None)
        await transition_job(
            job_id,
            "QUEUED",
            "PREPROCESSING",
            celery_task_id=task_id,
        )
    except Exception as e:
        logger.error("preprocess_dispatch_failed", job_id=str(job_id), error=str(e))
        await transition_job(
            job_id,
            "QUEUED",
            "FAILED",
            error_code="dispatch_error",
            error_message=str(e),
        )
        raise HTTPException(status_code=503, detail="Failed to dispatch preprocessing")

    return JobCreateResponse(job_id=job_id, status="PREPROCESSING")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_endpoint(
    job_id: UUID,
    _: None = Depends(verify_internal_token),
) -> JobStatusResponse:
    """Get job by ID."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        id=job["id"],
        tenant_id=job["tenant_id"],
        status=job["status"],
        tier_at_creation=job["tier_at_creation"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message"),
    )


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: UUID,
    _: None = Depends(verify_internal_token),
):
    """Retry a failed job. Resets to QUEUED and re-dispatches preprocessing."""
    from app.core.database import get_job_for_update

    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "FAILED":
        raise HTTPException(status_code=422, detail=f"Cannot retry job in state {job['status']}")

    if not validate_transition("FAILED", "QUEUED"):
        raise HTTPException(status_code=422, detail="Invalid transition for retry")
    await transition_job(
        job_id,
        "FAILED",
        "QUEUED",
        clear_errors=True,
    )
    try:
        task_id = call_svc04_preprocess(str(job_id), job["tenant_id"], None)
        await transition_job(job_id, "QUEUED", "PREPROCESSING", celery_task_id=task_id)
    except Exception as e:
        logger.error("retry_dispatch_failed", job_id=str(job_id), error=str(e))
        await transition_job(job_id, "QUEUED", "FAILED", error_code="retry_dispatch_error", error_message=str(e))
        raise HTTPException(status_code=503, detail="Failed to dispatch retry")

    return {"status": "ok", "job_id": str(job_id)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    _: None = Depends(verify_internal_token),
):
    """Cancel a job. Transitions to FAILED."""
    from app.core.database import get_job_for_update

    job = await get_job_for_update(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in ("DONE", "FAILED"):
        raise HTTPException(status_code=422, detail=f"Cannot cancel job in state {job['status']}")

    await transition_job(
        job_id,
        job["status"],
        "FAILED",
        error_code="cancelled",
        error_message="Job cancelled by user",
    )
    return {"status": "ok", "job_id": str(job_id)}
