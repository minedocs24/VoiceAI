"""Celery app per task GPU diarization."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "voicescribe_diarization_engine",
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
