"""Webhook client - async POST with exponential backoff retry."""

from __future__ import annotations

import time

import httpx
from structlog import get_logger

logger = get_logger(__name__)

RETRY_DELAYS = (10, 30, 90)  # seconds


def send_webhook(
    webhook_url: str,
    payload: dict,
    retries: tuple[int, ...] = RETRY_DELAYS,
) -> bool:
    """
    POST to webhook_url with payload. Retries with backoff 10s, 30s, 90s.
    Returns True if any attempt succeeds. On total failure: log only, do not raise.
    """
    for attempt, delay in enumerate(retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(webhook_url, json=payload)
            if 200 <= r.status_code < 300:
                logger.info("webhook_sent", url=webhook_url, status=r.status_code)
                return True
            logger.warning(
                "webhook_failed",
                url=webhook_url,
                status=r.status_code,
                attempt=attempt + 1,
            )
        except Exception as exc:
            logger.warning(
                "webhook_error",
                url=webhook_url,
                error=str(exc),
                attempt=attempt + 1,
            )

        if attempt < len(retries) - 1:
            time.sleep(delay)

    logger.error("webhook_all_retries_failed", url=webhook_url)
    return False
