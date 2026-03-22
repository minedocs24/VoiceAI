"""Tests for startup validation in Settings."""
import pytest


def test_settings_rejects_empty_jwt_secret(monkeypatch):
    """Settings must raise ValueError if JWT_SECRET_KEY is empty."""
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "some-token")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    # pydantic-settings reads env vars at __init__ time, so a fresh Settings()
    # call picks up monkeypatched values correctly.
    from app.core.config import Settings
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings()


def test_settings_rejects_empty_internal_token(monkeypatch):
    """Settings must raise ValueError if INTERNAL_SERVICE_TOKEN is empty."""
    monkeypatch.setenv("JWT_SECRET_KEY", "valid-secret")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    from app.core.config import Settings
    with pytest.raises(ValueError, match="INTERNAL_SERVICE_TOKEN"):
        Settings()


def test_settings_ok_with_valid_secrets(monkeypatch):
    """Settings instantiates when both secrets are provided."""
    monkeypatch.setenv("JWT_SECRET_KEY", "valid-secret")
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "valid-token")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    from app.core.config import Settings
    s = Settings()
    assert s.jwt_secret_key == "valid-secret"
    assert s.internal_service_token == "valid-token"
    assert s.swagger_ui_enabled is False
