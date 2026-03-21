"""Celery tasks for export and cleanup."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from celery.exceptions import Reject
from structlog import get_logger

from app.celery_app import celery_app
from app.core.config import settings
from app.models.schemas import ExportCompletePayload
from app.services.callback_client import send_export_callback
from app.services.export_service import run_export
from app.services.redis_client import publish_job_status
from app.services.webhook_client import send_webhook

logger = get_logger(__name__)


@celery_app.task(bind=True, acks_late=True, reject_on_worker_lost=True)
def export_task(
    self,
    job_id: str,
    tenant_id: str,
    ramdisk_path: str,
    *,
    transcription_raw: dict | None = None,
    diarization_raw: dict | None = None,
    tier: str = "FREE",
    webhook_url: str | None = None,
) -> dict:
    """
    Export task: generate documents, callback SVC-05, publish Redis, send webhook.
    """
    transcript_data = diarization_raw if diarization_raw else (transcription_raw or {})
    if not transcript_data:
        logger.error("export_task_no_data", job_id=job_id)
        send_export_callback(
            ExportCompletePayload(
                job_id=job_id,
                tenant_id=tenant_id,
                success=False,
                error_code="no_transcript_data",
                error_message="No transcription or diarization data provided",
            )
        )
        raise Reject(reason="no_transcript_data", requeue=False)

    try:
        download_urls, files = run_export(
            job_id=job_id,
            tenant_id=tenant_id,
            tier=tier,
            transcript_data=transcript_data,
            include_timestamps_txt=False,
        )
    except ValueError as e:
        if str(e) == "TIER_FORBIDDEN":
            send_export_callback(
                ExportCompletePayload(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    success=False,
                    error_code="TIER_FORBIDDEN",
                    error_message=str(e),
                )
            )
        raise Reject(reason=str(e), requeue=False)
    except Exception as exc:
        logger.exception("export_task_failed", job_id=job_id, error=str(exc))
        send_export_callback(
            ExportCompletePayload(
                job_id=job_id,
                tenant_id=tenant_id,
                success=False,
                error_code="export_failed",
                error_message=str(exc),
            )
        )
        raise Reject(reason=str(exc), requeue=False)

    completed_at = datetime.now(timezone.utc).isoformat()

    # Callback to SVC-05
    send_export_callback(
        ExportCompletePayload(
            job_id=job_id,
            tenant_id=tenant_id,
            success=True,
            download_urls=download_urls,
        )
    )

    # Publish Redis for WebSocket
    publish_job_status(
        job_id,
        "DONE",
        {"completed_at": completed_at, "download_urls": download_urls},
    )

    # Webhook async (fire-and-forget with retry inside)
    if webhook_url:
        send_webhook(
            webhook_url,
            {
                "job_id": job_id,
                "status": "DONE",
                "completed_at": completed_at,
                "download_urls": download_urls,
            },
        )

    return {"job_id": job_id, "download_urls": download_urls, "files": files}


@celery_app.task(bind=True)
def cleanup_expired_output_task(self) -> dict:
    """
    Celery Beat task: delete output files older than OUTPUT_TTL_DAYS.
    Report: files deleted, space freed, anomalies.
    """
    base = Path(settings.output_base_path)
    if not base.exists():
        return {"deleted": 0, "space_freed_gb": 0, "anomalies": []}

    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.output_ttl_days)
    deleted = 0
    space_freed = 0
    anomalies: list[str] = []

    for tenant_dir in base.iterdir():
        if not tenant_dir.is_dir():
            continue
        for job_dir in tenant_dir.iterdir():
            if not job_dir.is_dir():
                continue
            for f in job_dir.iterdir():
                if f.is_file():
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                        if mtime < cutoff:
                            size = f.stat().st_size
                            f.unlink()
                            deleted += 1
                            space_freed += size
                    except OSError as e:
                        anomalies.append(f"{f}: {e}")

    space_gb = round(space_freed / (1024**3), 2)
    logger.info(
        "cleanup_expired_output",
        deleted=deleted,
        space_freed_gb=space_gb,
        anomalies_count=len(anomalies),
    )
    return {
        "deleted": deleted,
        "space_freed_gb": space_gb,
        "anomalies": anomalies,
    }
