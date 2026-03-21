"""Security helpers for authentication and filesystem hardening."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException

from app.core.config import settings

TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,64}$")


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    """Verify X-Internal-Token. Raises 401 if missing/invalid."""
    expected = settings.internal_service_token
    if not expected:
        raise HTTPException(status_code=500, detail="Internal token not configured")
    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")


def validate_tenant_id(tenant_id: str) -> str:
    """Validate tenant slug format."""
    if not TENANT_ID_PATTERN.match(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-Id format")
    return tenant_id


def validate_job_id(job_id: str) -> str:
    """Validate UUID job identifier."""
    try:
        UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Job-Id format") from exc
    return job_id


def ensure_disk_space(min_required_bytes: int, target_path: str) -> None:
    """Ensure enough free disk space before accepting upload."""
    usage = shutil.disk_usage(target_path)
    if usage.free < min_required_bytes:
        raise HTTPException(
            status_code=503,
            detail="Insufficient disk space for upload",
        )


def get_disk_usage(path: str) -> shutil._ntuple_diskusage:
    """Return disk usage tuple for health and metrics."""
    return shutil.disk_usage(path)


def ensure_under_base(base: Path, candidate: Path) -> Path:
    """Ensure candidate is inside base path after resolution."""
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if base_resolved not in candidate_resolved.parents and candidate_resolved != base_resolved:
        raise HTTPException(status_code=400, detail="Invalid path outside storage base")
    return candidate_resolved


def ensure_no_symlink_components(path: Path, stop_at: Path | None = None) -> None:
    """Reject destination path if any existing component is a symlink."""
    current = Path(path.anchor) if path.is_absolute() else Path(".")
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if stop_at and current == stop_at:
            break
        if current.exists() and current.is_symlink():
            raise HTTPException(status_code=400, detail="Symlink not allowed in destination path")


def ensure_directory_read_write(path: str) -> None:
    """Check that a directory is readable and writable."""
    if not os.path.isdir(path):
        raise HTTPException(status_code=503, detail=f"Directory not found: {path}")
    if not os.access(path, os.R_OK | os.W_OK):
        raise HTTPException(status_code=503, detail=f"Directory not readable/writable: {path}")