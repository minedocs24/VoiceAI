"""Export API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import verify_internal_token, validate_job_id
from app.models.schemas import ExportRequest, ExportResponse
from app.services.export_service import run_export

router = APIRouter(prefix="/export", tags=["export"])

_FORMAT_TO_FILENAME = {
    "txt": "transcript.txt",
    "srt": "transcript.srt",
    "json": "transcript.json",
    "docx": "transcript.docx",
}

_FORMAT_CONTENT_TYPE = {
    "txt": "text/plain; charset=utf-8",
    "srt": "text/plain; charset=utf-8",
    "json": "application/json",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("", response_model=ExportResponse)
async def export_documents(
    body: ExportRequest,
    _: None = Depends(verify_internal_token),
) -> ExportResponse:
    """
    Generate documents from transcript/diarization data.
    Formati supportati per tier: Free (txt, srt), PRO/Enterprise (+ json, docx).
    """
    validate_job_id(body.job_id)
    try:
        download_urls, files = run_export(
            job_id=body.job_id,
            tenant_id=body.tenant_id,
            tier=body.tier,
            transcript_data=body.transcript,
            include_timestamps_txt=body.include_timestamps_txt,
            formats_requested=body.formats,
        )
        return ExportResponse(
            job_id=body.job_id,
            files=files,
            download_urls=download_urls,
        )
    except ValueError as e:
        if str(e) == "TIER_FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "TIER_FORBIDDEN",
                    "message": "Format not allowed for this tier",
                    "detail": "Requested format is only available for PRO/Enterprise tier",
                },
            )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download/{job_id}/{fmt}")
async def download_export(
    job_id: str,
    fmt: str,
    tenant_id: str,
    _: None = Depends(verify_internal_token),
) -> FileResponse:
    """
    Serve an exported file for a completed job.
    Called internally by the API Gateway — requires X-Internal-Token.
    tenant_id must be provided as a query parameter.
    """
    from app.core.config import settings

    fmt = fmt.lower()
    filename = _FORMAT_TO_FILENAME.get(fmt)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")

    file_path = Path(settings.output_base_path) / tenant_id / job_id / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Export file not found for job {job_id} format {fmt}. Ensure the job is DONE.",
        )

    return FileResponse(
        path=str(file_path),
        media_type=_FORMAT_CONTENT_TYPE[fmt],
        filename=filename,
    )
