"""Webhook notify endpoint - internal use for sending notifications."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import verify_internal_token
from app.services.webhook_client import send_webhook
from structlog import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


class WebhookNotifyRequest(BaseModel):
    job_id: str
    tenant_id: str
    webhook_url: str
    download_urls: dict[str, str]
    status: str = "DONE"


@router.post("/notify")
async def webhook_notify(
    body: WebhookNotifyRequest,
    _: None = Depends(verify_internal_token),
) -> dict:
    """
    Send webhook notification to tenant's webhook_url.
    Called internally after export. Async fire-and-forget with retry.
    """
    payload = {
        "job_id": body.job_id,
        "status": body.status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "download_urls": body.download_urls,
    }
    success = send_webhook(body.webhook_url, payload)
    return {"status": "ok", "webhook_sent": success}
