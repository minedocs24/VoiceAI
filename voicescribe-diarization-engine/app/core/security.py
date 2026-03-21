"""Security utilities."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Header, HTTPException


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    from app.core.config import settings

    if not settings.internal_service_token:
        return
    if not x_internal_token or x_internal_token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Token")


def validate_job_id(job_id: str) -> str:
    uuid_re = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    if not uuid_re.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    return job_id


def validate_tenant_id(tenant_id: str) -> str:
    if not tenant_id or len(tenant_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    if not re.match(r"^[a-zA-Z0-9\-]{1,64}$", tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    return tenant_id
