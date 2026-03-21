"""Security utilities."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    """Verify X-Internal-Token for inter-service calls."""
    from app.core.config import settings

    if not settings.internal_service_token:
        return
    if not x_internal_token or x_internal_token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Token")
