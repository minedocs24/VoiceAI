"""Storage path building and upload streaming helpers."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import get_ingestion_config, settings
from app.core.security import ensure_no_symlink_components, ensure_under_base
from app.services.validation import magic_buffer_size


@dataclass
class TempUploadResult:
    temp_path: Path
    size_bytes: int
    sha256: str
    prefix_bytes: bytes


def build_final_path(base: str, tenant_id: str, job_id: str, ext: str) -> tuple[str, str]:
    """Build final storage path from configured pattern and random uuid."""
    cfg = get_ingestion_config()
    pattern = cfg.get("storage", {}).get("path_pattern", "{base}/{tenant_id}/{job_id}/{uuid}.{ext}")
    file_uuid = str(uuid4())
    final_path = pattern.format(
        base=base.rstrip("/"),
        tenant_id=tenant_id,
        job_id=job_id,
        uuid=file_uuid,
        ext=ext,
    )
    return file_uuid, final_path


async def stream_to_temp(upload_file: UploadFile, expected_sha256: str | None = None) -> TempUploadResult:
    """Write uploaded content to temp file in chunks while computing SHA-256."""
    os.makedirs(settings.temp_upload_dir, exist_ok=True)

    max_size = settings.upload_max_bytes
    chunk_size = settings.upload_chunk_size
    magic_size = magic_buffer_size()

    hasher = hashlib.sha256()
    total = 0
    prefix = bytearray()

    fd, temp_name = tempfile.mkstemp(prefix="upload_", suffix=".tmp", dir=settings.temp_upload_dir)
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as output:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise HTTPException(status_code=413, detail="File too large")
                if len(prefix) < magic_size:
                    prefix.extend(chunk[: max(0, magic_size - len(prefix))])
                hasher.update(chunk)
                output.write(chunk)
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise

    digest = hasher.hexdigest()
    if expected_sha256 and digest.lower() != expected_sha256.strip().lower():
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Checksum mismatch")

    return TempUploadResult(
        temp_path=temp_path,
        size_bytes=total,
        sha256=digest,
        prefix_bytes=bytes(prefix),
    )


def move_temp_to_final(temp_path: Path, base_path: str, tenant_id: str, job_id: str, detected_ext: str) -> tuple[str, str]:
    """Move validated temp file into final destination path."""
    file_uuid, destination = build_final_path(base_path, tenant_id, job_id, detected_ext)

    base = Path(base_path)
    target = Path(destination)

    # Block path traversal and symlink abuse.
    ensure_under_base(base, target.parent)
    ensure_no_symlink_components(target.parent)

    target.parent.mkdir(parents=True, exist_ok=True)
    ensure_no_symlink_components(target.parent)

    os.replace(temp_path, target)
    return file_uuid, str(target)