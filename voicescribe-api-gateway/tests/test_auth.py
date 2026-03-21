"""Unit tests for authentication."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    decode_access_token,
    decode_refresh_token,
    hash_api_key,
    hash_password,
    validate_api_key_format,
    verify_password,
)


def test_hash_and_verify_password():
    """Password hashing and verification."""
    pwd = "secret123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_access_token():
    """JWT access token creation and decode."""
    token, _ = create_access_token("tenant-1", "FREE")
    payload = decode_access_token(token)
    assert payload["tenant_id"] == "tenant-1"
    assert payload["tier"] == "FREE"
    assert payload["type"] == "access"


def test_decode_expired_token():
    """Expired token raises."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings

    payload = {
        "tenant_id": "t1",
        "tier": "FREE",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        decode_access_token(token)
    assert exc.value.status_code == 401


def test_validate_api_key_format():
    """API key format validation."""
    assert validate_api_key_format("vs_live_" + "a" * 32)
    assert not validate_api_key_format("vs_live_short")
    assert not validate_api_key_format("invalid")
    assert not validate_api_key_format("vs_live_" + "a" * 32 + "!")


def test_hash_api_key():
    """API key hashing."""
    key = "vs_live_abcdef1234567890abcdef12345678"
    h = hash_api_key(key)
    assert len(h) == 64
    assert h == hash_api_key(key)
