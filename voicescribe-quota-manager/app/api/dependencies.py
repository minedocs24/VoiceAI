"""FastAPI dependencies: auth, validation."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Header, HTTPException, Request
from structlog import get_logger

from app.core.database import tenant_exists
logger = get_logger(__name__)

TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,64}$")


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
    request: Request | None = None,
) -> None:
    """Verify X-Internal-Token. Raises 401 if missing or invalid."""
    import os
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=500, detail="Internal token not configured")
    if not x_internal_token or x_internal_token != expected:
        client_ip = request.client.host if request and request.client else "unknown"
        logger.warning("Invalid or missing X-Internal-Token", client_ip=client_ip)
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")


async def validate_tenant_id(tenant_id: str) -> str:
    """Validate tenant_id format and existence. Raises 400/404."""
    if not TENANT_ID_PATTERN.match(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    exists = await tenant_exists(tenant_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id
