"""Auth endpoints: login, refresh, logout."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from structlog import get_logger

from app.core.config import get_gateway_config
from app.core.database import get_tenant_by_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.schemas import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
from app.services.redis_client import revoke_refresh_token, store_refresh_token
from app.services.rate_limit import check_auth_failure_rate_limit, record_auth_failure

logger = get_logger(__name__)

auth_router = APIRouter()


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
):
    """Login with email/password (Free Tier). Returns access and refresh tokens."""
    client_ip = request.client.host if request.client else "unknown"
    await check_auth_failure_rate_limit(client_ip)

    config = get_gateway_config().get("rate_limit", {})
    tenant = await get_tenant_by_email(body.email)
    if not tenant:
        await record_auth_failure(client_ip, config)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not tenant.get("password_hash"):
        await record_auth_failure(client_ip, config)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, tenant["password_hash"]):
        await record_auth_failure(client_ip, config)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token, expires_in = create_access_token(
        tenant_id=tenant["id"],
        tier=tenant["tier"],
    )
    refresh_token, refresh_expires = create_refresh_token(
        tenant_id=tenant["id"],
        tier=tenant["tier"],
    )
    payload = decode_refresh_token(refresh_token)
    await store_refresh_token(payload["jti"], tenant["id"], refresh_expires)

    logger.info("login_success", tenant_id=tenant["id"], tier=tenant["tier"])
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@auth_router.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest):
    """Exchange refresh token for new access token."""
    payload = decode_refresh_token(body.refresh_token)
    from app.services.redis_client import is_refresh_valid

    if not await is_refresh_valid(payload["jti"]):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    access_token, expires_in = create_access_token(
        tenant_id=payload["tenant_id"],
        tier=payload["tier"],
    )
    return RefreshResponse(access_token=access_token, expires_in=expires_in)


@auth_router.post("/logout")
async def logout(body: RefreshRequest):
    """Invalidate refresh token (logout)."""
    try:
        payload = decode_refresh_token(body.refresh_token)
        await revoke_refresh_token(payload["jti"])
        return {"message": "Logged out successfully"}
    except HTTPException:
        return {"message": "Logged out successfully"}
