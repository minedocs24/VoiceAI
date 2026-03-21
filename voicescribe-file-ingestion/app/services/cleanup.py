"""Temporary uploads cleanup routines."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from structlog import get_logger

from app.core.config import get_ingestion_config, settings

logger = get_logger(__name__)


def cleanup_temp_files_once() -> int:
    """Delete temporary files older than configured max age."""
    cfg = get_ingestion_config()
    max_age = int(cfg.get("temp_file_max_age_seconds", settings.temp_file_max_age_seconds))
    now = time.time()

    temp_dir = Path(settings.temp_upload_dir)
    if not temp_dir.exists():
        return 0

    removed = 0
    for item in temp_dir.iterdir():
        if not item.is_file():
            continue
        try:
            if now - item.stat().st_mtime > max_age:
                item.unlink(missing_ok=True)
                removed += 1
        except FileNotFoundError:
            continue
        except Exception as exc:
            logger.warning("temp_cleanup_failed", path=str(item), error=str(exc))

    return removed


async def cleanup_loop(stop_event: asyncio.Event) -> None:
    """Periodic cleanup loop used by lifespan."""
    interval = int(get_ingestion_config().get("temp_cleanup_interval_seconds", settings.temp_cleanup_interval_seconds))
    while not stop_event.is_set():
        removed = cleanup_temp_files_once()
        if removed:
            logger.info("temp_cleanup_removed", count=removed)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue