"""Security utilities: JWT, bcrypt, API key validation."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status
from structlog import get_logger

from app.core.config import settings
from app.models.schemas import AuthenticatedTenant

logger = get_logger(__name__)

API_KEY_PATTERN = re.compile(r"^vs_live_[a-zA-Z0-9]{32}$")


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(tenant_id: str, tier: str) -> tuple[str, int]:
    """Create JWT access token. Returns (token, expires_in_seconds)."""
    expires = timedelta(hours=settings.jwt_access_expires_hours)
    exp = datetime.now(timezone.utc) + expires
    payload = {
        "sub": tenant_id,
        "tenant_id": tenant_id,
        "tier": tier,
        "iat": datetime.now(timezone.utc),
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(expires.total_seconds())


def create_refresh_token(tenant_id: str, tier: str) -> tuple[str, int]:
    """Create refresh token. Returns (token, expires_in_seconds)."""
    expires = timedelta(days=settings.jwt_refresh_expires_days)
    exp = datetime.now(timezone.utc) + expires
    payload = {
        "sub": tenant_id,
        "tenant_id": tenant_id,
        "tier": tier,
        "iat": datetime.now(timezone.utc),
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    """Decode and validate access token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def decode_refresh_token(token: str) -> dict:
    """Decode and validate refresh token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


def hash_api_key(api_key: str) -> str:
    """SHA-256 hash of API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key_format(api_key: str) -> bool:
    """Check API key format vs_live_{32 alphanumeric}."""
    return bool(API_KEY_PATTERN.match(api_key))


def generate_api_key() -> str:
    """Generate new API key in vs_live_ format."""
    return f"vs_live_{secrets.token_hex(16)}"


def tier_to_priority(tier: str) -> int:
    """Map tier to Celery priority."""
    return {"FREE": 1, "PRO": 5, "ENTERPRISE": 10}.get(tier.upper(), 1)
