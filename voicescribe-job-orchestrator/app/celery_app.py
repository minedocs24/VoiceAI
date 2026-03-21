"""Celery app for sending tasks to worker queues."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_priority_for_tier, settings

celery_app = Celery(
    "voicescribe_job_orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)


def send_preprocess_task(job_id: str, tenant_id: str, tier: str, input_path: str | None = None) -> str:
    """Send preprocessing task to SVC-04 via cpu_tasks queue."""
    priority = get_priority_for_tier(tier)
    result = celery_app.send_task(
        "app.tasks.preprocess_task",
        args=[job_id, tenant_id],
        kwargs={"input_path": input_path},
        queue="cpu_tasks",
        priority=priority,
    )
    return result.id


def send_transcribe_task(job_id: str, tenant_id: str, tier: str, ramdisk_path: str) -> str:
    """Send transcription task to SVC-06 via gpu_tasks queue."""
    priority = get_priority_for_tier(tier)
    result = celery_app.send_task(
        "app.tasks.transcribe_task",
        args=[job_id, tenant_id, ramdisk_path],
        queue="gpu_tasks",
        priority=priority,
    )
    return result.id


def send_diarize_task(job_id: str, tenant_id: str, tier: str, ramdisk_path: str, transcription_raw: dict) -> str:
    """Send diarization task to SVC-07 via gpu_tasks queue."""
    priority = get_priority_for_tier(tier)
    result = celery_app.send_task(
        "app.tasks.diarize_task",
        args=[job_id, tenant_id, ramdisk_path],
        kwargs={"transcription_raw": transcription_raw},
        queue="gpu_tasks",
        priority=priority,
    )
    return result.id


def send_export_task(
    job_id: str,
    tenant_id: str,
    tier: str,
    ramdisk_path: str,
    transcription_raw: dict,
    diarization_raw: dict | None = None,
    webhook_url: str | None = None,
) -> str:
    """Send export task to SVC-08 via export_tasks queue."""
    priority = get_priority_for_tier(tier)
    result = celery_app.send_task(
        "app.tasks.export_task",
        args=[job_id, tenant_id, ramdisk_path],
        kwargs={
            "transcription_raw": transcription_raw,
            "diarization_raw": diarization_raw,
            "tier": tier,
            "webhook_url": webhook_url,
        },
        queue="export_tasks",
        priority=priority,
    )
    return result.id
