"""PostgreSQL async connection pool and repository operations."""

from __future__ import annotations

import asyncpg
from structlog import get_logger

from app.core.config import settings
from app.models.schemas import FileRecord

logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


def get_pool_url() -> str:
    """Convert SQLAlchemy-style URL to asyncpg format."""
    url = settings.database_url
    if not url:
        return ""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def init_pool(min_size: int = 1, max_size: int = 8, command_timeout: int = 30) -> asyncpg.Pool | None:
    """Initialize connection pool."""
    global _pool
    url = get_pool_url()
    if not url:
        logger.warning("database_url_not_set")
        return None
    try:
        _pool = await asyncpg.create_pool(
            url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
        await _pool.fetchval("SELECT 1")
        return _pool
    except Exception as exc:
        logger.error("postgres_init_failed", error=str(exc))
        return None


async def close_pool() -> None:
    """Close pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def db_ping() -> bool:
    """Health check for PostgreSQL."""
    if _pool is None:
        return False
    try:
        await _pool.fetchval("SELECT 1")
        return True
    except Exception:
        return False


async def ensure_schema() -> None:
    """Create table if missing."""
    if _pool is None:
        return
    await _pool.execute(
        """
        CREATE TABLE IF NOT EXISTS ingested_files (
            id BIGSERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            job_id UUID NOT NULL,
            file_uuid UUID NOT NULL,
            storage_path TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            detected_ext VARCHAR(16) NOT NULL,
            sha256 CHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ingested_files_job_id ON ingested_files(job_id);
        CREATE INDEX IF NOT EXISTS idx_ingested_files_tenant_job ON ingested_files(tenant_id, job_id);
        """
    )


async def insert_file_record(
    tenant_id: str,
    job_id: str,
    file_uuid: str,
    storage_path: str,
    size_bytes: int,
    detected_ext: str,
    sha256: str,
) -> FileRecord:
    """Insert uploaded file record."""
    if _pool is None:
        raise RuntimeError("PostgreSQL unavailable")

    row = await _pool.fetchrow(
        """
        INSERT INTO ingested_files (
            tenant_id, job_id, file_uuid, storage_path, size_bytes, detected_ext, sha256
        ) VALUES ($1, $2::uuid, $3::uuid, $4, $5, $6, $7)
        RETURNING tenant_id, job_id::text, file_uuid::text, storage_path, size_bytes,
                  detected_ext, sha256, created_at, updated_at
        """,
        tenant_id,
        job_id,
        file_uuid,
        storage_path,
        size_bytes,
        detected_ext,
        sha256,
    )
    return FileRecord(
        tenant_id=row["tenant_id"],
        job_id=row["job_id"],
        file_uuid=row["file_uuid"],
        storage_path=row["storage_path"],
        size_bytes=row["size_bytes"],
        detected_ext=row["detected_ext"],
        sha256=row["sha256"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_files_by_job(job_id: str) -> list[FileRecord]:
    """Get all files linked to job_id."""
    if _pool is None:
        raise RuntimeError("PostgreSQL unavailable")
    rows = await _pool.fetch(
        """
        SELECT tenant_id, job_id::text, file_uuid::text, storage_path, size_bytes,
               detected_ext, sha256, created_at, updated_at
        FROM ingested_files
        WHERE job_id = $1::uuid
        ORDER BY created_at DESC
        """,
        job_id,
    )
    return [
        FileRecord(
            tenant_id=row["tenant_id"],
            job_id=row["job_id"],
            file_uuid=row["file_uuid"],
            storage_path=row["storage_path"],
            size_bytes=row["size_bytes"],
            detected_ext=row["detected_ext"],
            sha256=row["sha256"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def get_latest_file_for_job(job_id: str) -> FileRecord | None:
    """Get newest file for a job."""
    files = await list_files_by_job(job_id)
    return files[0] if files else None


async def delete_files_by_job(job_id: str) -> list[FileRecord]:
    """Delete DB records and return deleted entries."""
    if _pool is None:
        raise RuntimeError("PostgreSQL unavailable")
    rows = await _pool.fetch(
        """
        DELETE FROM ingested_files
        WHERE job_id = $1::uuid
        RETURNING tenant_id, job_id::text, file_uuid::text, storage_path, size_bytes,
                  detected_ext, sha256, created_at, updated_at
        """,
        job_id,
    )
    return [
        FileRecord(
            tenant_id=row["tenant_id"],
            job_id=row["job_id"],
            file_uuid=row["file_uuid"],
            storage_path=row["storage_path"],
            size_bytes=row["size_bytes"],
            detected_ext=row["detected_ext"],
            sha256=row["sha256"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]