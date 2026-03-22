"""Jobs endpoints: transcribe, list, get, download, WebSocket."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from structlog import get_logger

from app.core.config import get_gateway_config, settings
from app.core.database import get_job, insert_job, list_jobs_for_tenant
from app.models.schemas import AuthenticatedTenant, ErrorResponse, JobListResponse, JobStatus, TranscribeResponse
from app.api.dependencies import get_authenticated_tenant
from app.services.svc02_client import delete_files_by_job, upload_file as svc02_upload
from app.services.svc03_client import check_quota, consume_quota, rollback_quota
from app.services.svc05_client import dispatch_job as svc05_dispatch
from app.services.rate_limit import check_rate_limit

logger = get_logger(__name__)

jobs_router = APIRouter()

# Celery/Redis - placeholder for job publishing (Stage 1 may use simple Redis queue)
# For now we insert job and would publish to Celery; SVC-05 Job Orchestrator consumes
CELERY_APP = None  # Will be configured when Celery is wired


def _serialize_job(row: dict) -> JobStatus:
    return JobStatus(
        id=str(row["id"]),
        tenant_id=row["tenant_id"],
        status=row["status"],
        tier_at_creation=row["tier_at_creation"],
        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        completed_at=row["completed_at"].isoformat() if row.get("completed_at") and hasattr(row["completed_at"], "isoformat") else None,
        error_message=row.get("error_message"),
    )


@jobs_router.post("/transcribe", status_code=202)
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    tenant: Annotated[AuthenticatedTenant, Depends(get_authenticated_tenant)] = None,
):
    """Upload file for transcription. Free Tier: quota + duration checks. PRO/Enterprise: no quota."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    config = get_gateway_config()
    rate_config = config.get("rate_limit", {})
    tier_features = config.get("tier_features", {})

    # Rate limit
    allowed, limit, remaining, reset_ts = await check_rate_limit(tenant.tenant_id, tenant.tier, rate_config)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_ts),
                "Retry-After": str(max(1, reset_ts - int(datetime.now(timezone.utc).timestamp()))),
            },
        )

    job_id = str(uuid.uuid4())
    content = await file.read()
    filename = file.filename or "audio.mp3"
    free_tier = tenant.tier == "FREE"

    try:
        # 1. Upload to SVC-02 (with X-Free-Tier for Free - SVC-02 does duration check and returns 422 if > 30 min)
        await svc02_upload(
            file_content=content,
            filename=filename,
            tenant_id=tenant.tenant_id,
            job_id=job_id,
            free_tier=free_tier,
            request_id=request_id,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            raise HTTPException(
                status_code=422,
                detail="File duration exceeds 30 minutes for Free Tier. Upgrade to Pro for longer files.",
            )
        if e.response.status_code in (400, 413):
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text or "Upload failed")
        raise HTTPException(status_code=503, detail="File ingestion service unavailable")
    except httpx.RequestError as e:
        logger.error("svc02_upload_failed", error=str(e), request_id=request_id)
        raise HTTPException(status_code=503, detail="File ingestion service unavailable")

    # 2. Free Tier: check and consume quota
    if free_tier:
        try:
            check_resp = await check_quota(tenant.tenant_id, request_id)
            if not check_resp.get("allowed", True):
                await delete_files_by_job(job_id, request_id)
                raise HTTPException(
                    status_code=429,
                    detail="Daily quota exceeded",
                    headers={"Retry-After": "86400"},
                )

            consume_resp = await consume_quota(tenant.tenant_id, request_id)
            if consume_resp.get("consumed") is False or consume_resp.get("remaining", 0) < 0:
                await delete_files_by_job(job_id, request_id)
                raise HTTPException(
                    status_code=429,
                    detail="Daily quota exceeded",
                    headers={"Retry-After": "86400"},
                )
        except HTTPException:
            raise
        except Exception as e:
            await delete_files_by_job(job_id, request_id)
            logger.error("quota_check_failed", error=str(e), request_id=request_id)
            raise HTTPException(status_code=503, detail="Quota service unavailable")

    # 3. Insert job and dispatch to SVC-05 (triggers preprocessing pipeline)
    try:
        from app.core.security import tier_to_priority
        priority = tier_to_priority(tenant.tier)
        await insert_job(job_id, tenant.tenant_id, tenant.tier, "QUEUED", priority)
    except Exception as e:
        if free_tier:
            await rollback_quota(tenant.tenant_id, request_id)
        await delete_files_by_job(job_id, request_id)
        logger.error("insert_job_failed", error=str(e), request_id=request_id)
        raise HTTPException(status_code=503, detail="Failed to create job")

    try:
        await svc05_dispatch(
            job_id=job_id,
            tenant_id=tenant.tenant_id,
            tier=tenant.tier,
            duration_seconds=None,
            request_id=request_id,
        )
    except Exception as e:
        if free_tier:
            await rollback_quota(tenant.tenant_id, request_id)
        await delete_files_by_job(job_id, request_id)
        logger.error("svc05_dispatch_failed", error=str(e), request_id=request_id)
        raise HTTPException(status_code=503, detail="Failed to start job processing")

    logger.info(
        "transcribe_queued",
        job_id=job_id,
        tenant_id=tenant.tenant_id,
        tier=tenant.tier,
        request_id=request_id,
    )
    response = TranscribeResponse(job_id=job_id, status="QUEUED", message="Job queued for processing")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=202,
        content=response.model_dump(),
        headers={
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining - 1),
            "X-RateLimit-Reset": str(reset_ts),
        },
    )


@jobs_router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    tenant: Annotated[AuthenticatedTenant, Depends(get_authenticated_tenant)] = None,
):
    """List jobs for authenticated tenant."""
    if limit < 1 or limit > 100:
        limit = 50
    if offset < 0:
        offset = 0
    rows, total = await list_jobs_for_tenant(tenant.tenant_id, limit=limit, offset=offset)
    return JobListResponse(jobs=[_serialize_job(r) for r in rows], total=total)


@jobs_router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    request: Request,
    tenant: Annotated[AuthenticatedTenant, Depends(get_authenticated_tenant)] = None,
):
    """Get job by ID. Must be owner."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["tenant_id"] != tenant.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


@jobs_router.get("/jobs/{job_id}/download/{fmt}")
async def download_job(
    job_id: str,
    fmt: str,
    request: Request,
    tenant: Annotated[AuthenticatedTenant, Depends(get_authenticated_tenant)] = None,
):
    """Download job result in specified format. Free Tier: txt, srt, json only. PRO+: docx, vtt."""
    config = get_gateway_config()
    tier_features = config.get("tier_features", {})
    free_formats = tier_features.get("free", {}).get("export_formats", ["txt", "srt", "json"])
    pro_formats = tier_features.get("pro", {}).get("export_formats", ["txt", "srt", "json", "docx", "vtt"])

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["tenant_id"] != tenant.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")

    allowed = pro_formats if tenant.tier in ("PRO", "ENTERPRISE") else free_formats
    if fmt.lower() not in [f.lower() for f in allowed]:
        raise HTTPException(
            status_code=403,
            detail=f"Format {fmt} not available for your tier. Allowed: {', '.join(allowed)}",
        )

    if job["status"] != "DONE":
        raise HTTPException(status_code=404, detail="Export not ready — job has not completed yet")

    # Proxy to SVC-08 Export Service
    svc08_url = settings.svc08_url.rstrip("/")
    download_url = f"{svc08_url}/export/download/{job_id}/{fmt.lower()}?tenant_id={tenant.tenant_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
            resp = await client.get(
                download_url,
                headers={"X-Internal-Token": settings.internal_service_token},
            )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Export file not found — ensure the job is DONE")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Export service error")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            headers={"Content-Disposition": resp.headers.get("content-disposition", f'attachment; filename="transcript.{fmt.lower()}"')},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("svc08_proxy_failed", error=str(e), job_id=job_id, fmt=fmt)
        raise HTTPException(status_code=503, detail="Export service unavailable")
