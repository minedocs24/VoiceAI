"""Database operations for jobs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


def _get_url() -> str:
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_get_url(), min_size=1, max_size=10, command_timeout=30)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def create_job(
    job_id: UUID,
    tenant_id: str,
    tier: str,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Create job in QUEUED state. Returns job row."""
    priority = 1 if tier.upper() == "FREE" else (5 if tier.upper() == "PRO" else 10)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO jobs (id, tenant_id, tier_at_creation, status, priority, duration_seconds, status_history)
            VALUES ($1, $2, $3::tier_at_creation, 'QUEUED', $4, $5, $6::jsonb)
            """,
            job_id,
            tenant_id,
            tier.upper(),
            priority,
            duration_seconds,
            '[]',
        )
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
        return dict(row) if row else {}


async def get_job_for_update(job_id: UUID) -> dict[str, Any] | None:
    """Get job with FOR UPDATE lock."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM jobs WHERE id = $1 FOR UPDATE",
            job_id,
        )
        return dict(row) if row else None


async def get_job(job_id: UUID) -> dict[str, Any] | None:
    """Get job by ID (no lock)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
        return dict(row) if row else None


async def transition_job(
    job_id: UUID,
    from_status: str,
    to_status: str,
    *,
    ramdisk_path: str | None = None,
    transcription_raw: dict | None = None,
    diarization_raw: dict | None = None,
    gpu_inference_ms: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    celery_task_id: str | None = None,
    stage_duration_seconds: float | None = None,
    clear_errors: bool = False,
) -> bool:
    """
    Atomically transition job state. Validates transition.
    Appends to status_history. Returns True on success.
    """
    from app.services.state_machine import validate_transition

    if not validate_transition(from_status, to_status):
        return False

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id, status, status_history FROM jobs WHERE id = $1 FOR UPDATE",
                job_id,
            )
            if not row or row["status"] != from_status:
                return False

            history = list(row["status_history"] or [])
            history.append({
                "from": from_status,
                "to": to_status,
                "at": datetime.now(timezone.utc).isoformat(),
                "stage_duration_seconds": stage_duration_seconds,
            })

            updates = ["status = $2", "status_history = $3::jsonb", "updated_at = NOW()"]
            params: list[Any] = [job_id, to_status, json.dumps(history)]
            idx = 4
            if ramdisk_path is not None:
                updates.append(f"ramdisk_path = ${idx}")
                params.append(ramdisk_path)
                idx += 1
            if transcription_raw is not None:
                updates.append(f"transcription_raw = ${idx}::jsonb")
                params.append(transcription_raw)
                idx += 1
            if diarization_raw is not None:
                updates.append(f"diarization_raw = ${idx}::jsonb")
                params.append(diarization_raw)
                idx += 1
            if gpu_inference_ms is not None:
                updates.append(f"gpu_inference_ms = ${idx}")
                params.append(gpu_inference_ms)
                idx += 1
            if clear_errors:
                updates.append("error_code = NULL, error_message = NULL")
            elif error_code is not None or error_message is not None:
                if error_code is not None:
                    updates.append(f"error_code = ${idx}")
                    params.append(error_code)
                    idx += 1
                if error_message is not None:
                    updates.append(f"error_message = ${idx}")
                    params.append(error_message)
                    idx += 1
            if celery_task_id is not None:
                updates.append(f"celery_task_id = ${idx}")
                params.append(celery_task_id)
                idx += 1
            if to_status in ("DONE", "FAILED"):
                updates.append("completed_at = NOW()")

            await conn.execute(
                f"UPDATE jobs SET {', '.join(updates)} WHERE id = $1",
                *params,
            )
            return True


async def count_jobs_by_status() -> dict[str, int]:
    """Count jobs per status for metrics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        )
        return {r["status"]: r["cnt"] for r in rows}
