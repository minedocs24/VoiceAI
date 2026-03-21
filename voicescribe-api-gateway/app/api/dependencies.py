"""FastAPI dependencies for authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_gateway_config
from app.core.database import get_tenant_by_email, verify_api_key
from app.core.security import (
    decode_access_token,
    hash_api_key,
    validate_api_key_format,
)
from app.models.schemas import AuthenticatedTenant
from app.services.redis_client import get_cached_tenant, is_refresh_valid, set_cached_tenant

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_authenticated_tenant(
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> AuthenticatedTenant:
    """
    Accept either Bearer JWT or X-API-Key. Returns AuthenticatedTenant.
    """
    config = get_gateway_config()
    excluded = config.get("auth_excluded_paths", [])

    # Try Bearer token first
    if authorization and authorization.credentials:
        try:
            payload = decode_access_token(authorization.credentials)
            return AuthenticatedTenant(
                tenant_id=payload["tenant_id"],
                tier=payload["tier"],
                permissions=[],
            )
        except HTTPException:
            raise

    # Try API Key
    if x_api_key:
        if not validate_api_key_format(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API key format")
        key_hash = hash_api_key(x_api_key)

        # Check cache first
        cached = await get_cached_tenant(key_hash)
        if cached:
            return AuthenticatedTenant(
                tenant_id=cached["id"],
                tier=cached["tier"],
                permissions=[],
            )

        # Verify against DB
        tenant = await verify_api_key(key_hash)
        if tenant:
            await set_cached_tenant(key_hash, tenant)
            return AuthenticatedTenant(
                tenant_id=tenant["id"],
                tier=tenant["tier"],
                permissions=[],
            )
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    raise HTTPException(
        status_code=401,
        detail="Missing authentication. Provide Authorization: Bearer <token> or X-API-Key",
    )


async def get_optional_tenant(
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> AuthenticatedTenant | None:
    """Optional auth - returns None if no credentials provided."""
    if not authorization and not x_api_key:
        return None
    return await get_authenticated_tenant(authorization=authorization, x_api_key=x_api_key)
