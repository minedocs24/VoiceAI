"""Export API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import verify_internal_token, validate_job_id
from app.models.schemas import ExportRequest, ExportResponse
from app.services.export_service import run_export

router = APIRouter(prefix="/export", tags=["export"])


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
