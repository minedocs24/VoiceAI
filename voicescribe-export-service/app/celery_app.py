"""Celery app for export tasks and beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "voicescribe_export_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_default_queue=settings.celery_queue_name,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)

# Beat schedule - cleanup at midnight UTC
celery_app.conf.beat_schedule = {
    "cleanup-expired-output": {
        "task": "app.tasks.cleanup_expired_output_task",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": settings.celery_queue_name},
    },
}
