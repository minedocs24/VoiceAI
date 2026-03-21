"""Client per callback a SVC-05 (export-complete)."""

from __future__ import annotations

import time

import httpx
from structlog import get_logger

from app.core.config import settings
from app.models.schemas import ExportCompletePayload

logger = get_logger(__name__)


def send_export_callback(payload: ExportCompletePayload, retries: int = 5) -> bool:
    url = f"{settings.svc05_callback_url.rstrip('/')}/callbacks/export-complete"
    headers = {"X-Internal-Token": settings.internal_service_token}
    body = payload.model_dump(mode="json")

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
            if response.status_code in (200, 202):
                return True
            logger.warning(
                "export_callback_failed",
                status=response.status_code,
                body=response.text[:300],
            )
        except Exception as exc:
            logger.warning("export_callback_error", attempt=attempt + 1, error=str(exc))

        if attempt < retries - 1:
            time.sleep(2**attempt)

    return False
