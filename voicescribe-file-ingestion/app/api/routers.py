"""Main API routes for ingestion service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from structlog import get_logger

from app.core.config import settings
from app.core.database import (
    delete_files_by_job,
    get_latest_file_for_job,
    insert_file_record,
    list_files_by_job,
)
from app.core.metrics import UPLOAD_REJECTED_TOTAL, UPLOAD_SIZE_BYTES, UPLOAD_SUCCESS_TOTAL
from app.core.security import (
    ensure_disk_space,
    validate_job_id,
    validate_tenant_id,
    verify_internal_token,
)
from app.models.schemas import DeleteResponse, FileListResponse, ProbeResponse, UploadResponse
from app.services.probe import probe_media_file
from app.services.storage import move_temp_to_final, stream_to_temp
from app.services.validation import (
    detect_format_from_magic,
    ensure_extension_coherent,
    extract_extension,
    validate_extension,
)

logger = get_logger(__name__)

router = APIRouter(tags=["ingestion"])


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")] = "",
    x_job_id: Annotated[str, Header(alias="X-Job-Id")] = "",
    x_expected_sha256: Annotated[str | None, Header(alias="X-Expected-SHA256")] = None,
    x_free_tier: Annotated[str | None, Header(alias="X-Free-Tier")] = None,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> UploadResponse:
    """Upload file in streaming mode with strict validations."""
    tenant_id = validate_tenant_id(x_tenant_id)
    job_id = validate_job_id(x_job_id)

    os.makedirs(settings.storage_base_path, exist_ok=True)
    ensure_disk_space(min_required_bytes=settings.upload_max_bytes * 2, target_path=settings.storage_base_path)

    declared_ext = extract_extension(file.filename)
    validate_extension(declared_ext)

    try:
        temp_result = await stream_to_temp(file, expected_sha256=x_expected_sha256)
    except HTTPException as exc:
        if exc.status_code == 413:
            UPLOAD_REJECTED_TOTAL.labels(reason="size_exceeded").inc()
        elif str(exc.detail) == "Checksum mismatch":
            UPLOAD_REJECTED_TOTAL.labels(reason="checksum_mismatch").inc()
        raise

    try:
        detected_ext = detect_format_from_magic(temp_result.prefix_bytes)
        ensure_extension_coherent(declared_ext, detected_ext)
    except HTTPException:
        UPLOAD_REJECTED_TOTAL.labels(reason="validation_format").inc()
        temp_result.temp_path.unlink(missing_ok=True)
        raise

    free_tier_enabled = str(x_free_tier).lower() in {"1", "true", "yes"}
    if free_tier_enabled:
        try:
            probe_data = await probe_media_file(job_id=f"temp:{job_id}", file_path=str(temp_result.temp_path))
        except HTTPException:
            UPLOAD_REJECTED_TOTAL.labels(reason="probe_failed").inc()
            temp_result.temp_path.unlink(missing_ok=True)
            raise

        if probe_data["duration_seconds"] > settings.free_tier_max_duration_seconds:
            UPLOAD_REJECTED_TOTAL.labels(reason="free_tier_duration").inc()
            temp_result.temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Free tier duration exceeded: {probe_data['duration_seconds']}s "
                    f"> {settings.free_tier_max_duration_seconds}s"
                ),
            )

    file_uuid, final_path = move_temp_to_final(
        temp_path=temp_result.temp_path,
        base_path=settings.storage_base_path,
        tenant_id=tenant_id,
        job_id=job_id,
        detected_ext=detected_ext,
    )

    try:
        record = await insert_file_record(
            tenant_id=tenant_id,
            job_id=job_id,
            file_uuid=file_uuid,
            storage_path=final_path,
            size_bytes=temp_result.size_bytes,
            detected_ext=detected_ext,
            sha256=temp_result.sha256,
        )
    except Exception as exc:
        Path(final_path).unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=f"Database insert failed: {exc}") from exc

    UPLOAD_SUCCESS_TOTAL.inc()
    UPLOAD_SIZE_BYTES.observe(temp_result.size_bytes)
    logger.info("upload_success", tenant_id=tenant_id, job_id=job_id, file_uuid=file_uuid)

    return UploadResponse(file=record)


@router.get("/files/{job_id}", response_model=FileListResponse)
async def get_files(
    job_id: str,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> FileListResponse:
    """List files for a job."""
    validated_job = validate_job_id(job_id)
    files = await list_files_by_job(validated_job)
    return FileListResponse(job_id=validated_job, files=files)


@router.delete("/files/{job_id}", response_model=DeleteResponse)
async def delete_files(
    job_id: str,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> DeleteResponse:
    """Delete files metadata and storage objects for a job."""
    validated_job = validate_job_id(job_id)
    deleted = await delete_files_by_job(validated_job)

    count = 0
    for record in deleted:
        try:
            Path(record.storage_path).unlink(missing_ok=True)
            count += 1
        except Exception:
            continue

    return DeleteResponse(job_id=validated_job, deleted_files=count)


@router.get("/probe/{job_id}", response_model=ProbeResponse)
async def probe(
    job_id: str,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> ProbeResponse:
    """Run (or fetch cached) ffprobe metadata for job file."""
    validated_job = validate_job_id(job_id)
    record = await get_latest_file_for_job(validated_job)
    if not record:
        raise HTTPException(status_code=404, detail="No file found for job")

    probe_data = await probe_media_file(validated_job, record.storage_path)
    return ProbeResponse(**probe_data)