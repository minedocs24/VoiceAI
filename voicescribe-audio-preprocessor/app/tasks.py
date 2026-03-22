"""Celery tasks for audio preprocessing."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
from celery.exceptions import Reject

from app.celery_app import celery_app
from structlog import get_logger

from app.core.config import settings
from app.core.metrics import CALLBACK_RETRIES_TOTAL, PREPROCESS_DURATION_SECONDS, PREPROCESS_TASKS_TOTAL, QUOTA_CHECK_FAILURES_TOTAL
from app.services.ffmpeg_pipeline import FFmpegTransientError, InputError, run_preprocess

logger = get_logger(__name__)

RETRY_BACKOFF = [30, 90, 270]
MAX_RETRIES = 3


def _check_quota(tenant_id: str) -> bool:
    """Check quota via SVC-03. Returns True if allowed."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{settings.svc03_url.rstrip('/')}/quota/check/{tenant_id}",
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            if r.status_code != 200:
                return False
            data = r.json()
            return data.get("allowed", False)
    except Exception as e:
        logger.warning("quota_check_failed", tenant_id=tenant_id, error=str(e))
        return False


def _rollback_quota(tenant_id: str) -> None:
    """Rollback quota via SVC-03. Best-effort."""
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                f"{settings.svc03_url.rstrip('/')}/quota/rollback/{tenant_id}",
                headers={"X-Internal-Token": settings.internal_service_token},
            )
    except Exception as e:
        logger.warning("quota_rollback_failed", tenant_id=tenant_id, error=str(e))


def _notify_svc05(
    job_id: str,
    tenant_id: str,
    success: bool,
    ramdisk_path: str | None = None,
    sha256: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> bool:
    """Notify SVC-05 of preprocessing result. Returns True on success."""
    url = f"{settings.svc05_url.rstrip('/')}/callbacks/preprocessing-complete"
    payload: dict[str, Any] = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "success": success,
    }
    if success:
        payload["ramdisk_path"] = ramdisk_path
        payload["sha256"] = sha256
    else:
        payload["error_code"] = error_code or "preprocess_failed"
        payload["error_message"] = error_message or "Unknown error"

    for attempt in range(5):
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    url,
                    json=payload,
                    headers={"X-Internal-Token": settings.internal_service_token},
                )
                if r.status_code in (200, 202):
                    return True
                logger.warning("callback_failed", status=r.status_code, body=r.text[:200])
        except Exception as e:
            logger.warning("callback_error", attempt=attempt + 1, error=str(e))
            CALLBACK_RETRIES_TOTAL.inc()
        if attempt < 4:
            time.sleep(2 ** attempt)
    return False


def _get_input_path(job_id: str, tenant_id: str, input_path: str | None) -> str:
    """Resolve input file path. If input_path given, use it; else fetch from SVC-02."""
    if input_path:
        p = Path(input_path)
        if p.is_absolute():
            return str(p)
        return str(Path(settings.storage_base_path) / input_path)

    # Fetch from SVC-02
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{settings.svc02_url.rstrip('/')}/files/{job_id}",
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            if r.status_code != 200:
                raise InputError(f"No files for job: {r.status_code}")
            data = r.json()
            files = data.get("files", [])
            if not files:
                raise InputError("No files found for job")
            storage_path = files[0].get("storage_path")
            if not storage_path:
                raise InputError("File has no storage_path")
            p = Path(storage_path)
            if not p.is_absolute():
                return str(Path(settings.storage_base_path) / storage_path)
            return storage_path
    except InputError:
        raise
    except Exception as e:
        raise InputError(f"Cannot resolve input: {e}") from e


@celery_app.task(bind=True, acks_late=True, reject_on_worker_lost=True)
def preprocess_task(
    self,
    job_id: str,
    tenant_id: str,
    input_path: str | None = None,
) -> dict[str, Any]:
    """
    Preprocess audio file for job.
    Raises Reject for input errors (no retry), retries for system errors.
    """
    try:
        input_file = _get_input_path(job_id, tenant_id, input_path)
    except InputError as e:
        PREPROCESS_TASKS_TOTAL.labels(status="input_error").inc()
        _notify_svc05(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="input_error",
            error_message=str(e),
        )
        raise Reject(reason=str(e), requeue=False)

    # Secondary quota guard — check only, do NOT rollback.
    # Quota was already consumed at the gateway layer; rolling back here
    # would grant the tenant a free extra job if Redis evicted the key.
    if not _check_quota(tenant_id):
        QUOTA_CHECK_FAILURES_TOTAL.inc()
        PREPROCESS_TASKS_TOTAL.labels(status="quota_exceeded").inc()
        logger.warning("secondary_quota_check_failed", job_id=job_id, tenant_id=tenant_id)
        _notify_svc05(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="quota_exceeded",
            error_message="Quota check failed before processing",
        )
        raise Reject(reason="Quota exceeded", requeue=False)

    output_path = str(Path(settings.ramdisk_path) / f"{job_id}.wav")
    start = time.perf_counter()

    try:
        sha256 = run_preprocess(
            input_path=input_file,
            output_path=output_path,
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
    except InputError as e:
        PREPROCESS_TASKS_TOTAL.labels(status="input_error").inc()
        _notify_svc05(
            job_id=job_id,
            tenant_id=tenant_id,
            success=False,
            error_code="input_error",
            error_message=str(e),
        )
        raise Reject(reason=str(e), requeue=False)
    except FFmpegTransientError as e:
        retries = self.request.retries
        if retries >= MAX_RETRIES - 1:
            PREPROCESS_TASKS_TOTAL.labels(status="system_error").inc()
            _notify_svc05(
                job_id=job_id,
                tenant_id=tenant_id,
                success=False,
                error_code="system_error",
                error_message=str(e),
            )
            raise Reject(reason=str(e), requeue=False)
        raise self.retry(countdown=RETRY_BACKOFF[retries], exc=e)

    elapsed = time.perf_counter() - start
    PREPROCESS_DURATION_SECONDS.observe(elapsed)
    PREPROCESS_TASKS_TOTAL.labels(status="success").inc()

    ok = _notify_svc05(
        job_id=job_id,
        tenant_id=tenant_id,
        success=True,
        ramdisk_path=output_path,
        sha256=sha256,
    )
    if not ok:
        # Processing done, only notification failed - retry notification only
        for _ in range(5):
            if _notify_svc05(
                job_id=job_id,
                tenant_id=tenant_id,
                success=True,
                ramdisk_path=output_path,
                sha256=sha256,
            ):
                break
            time.sleep(2)

    return {"job_id": job_id, "ramdisk_path": output_path, "sha256": sha256}
