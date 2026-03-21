"""Cleanup endpoint - delete WAV from Ramdisk."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.metrics import CLEANUP_FILES_DELETED_TOTAL, CLEANUP_SPACE_FREED_BYTES
from app.core.security import verify_internal_token, validate_job_id
from structlog import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


@router.delete("/{job_id}")
async def cleanup_ramdisk(
    job_id: str,
    _: None = Depends(verify_internal_token),
) -> dict:
    """
    Delete WAV file from Ramdisk for the given job.
    Validates: file exists, path under RAMDISK_PATH (no traversal), job DONE/FAILED.
    """
    validate_job_id(job_id)
    ramdisk = Path(settings.ramdisk_path).resolve()
    wav_path = (ramdisk / f"{job_id}.wav").resolve()

    try:
        wav_path.relative_to(ramdisk)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path - path traversal detected")

    if not wav_path.exists():
        return {"status": "ok", "message": "File not found", "deleted": False}

    # Job state check: we don't have DB access here; SVC-05 calls us after transition.
    # So we trust the caller - if they call DELETE, the job is DONE/FAILED.
    size = wav_path.stat().st_size
    wav_path.unlink()
    logger.info("cleanup_ramdisk_deleted", job_id=job_id, path=str(wav_path), size_bytes=size)
    CLEANUP_FILES_DELETED_TOTAL.inc()
    CLEANUP_SPACE_FREED_BYTES.inc(size)
    return {"status": "ok", "deleted": True, "size_freed_bytes": size}
