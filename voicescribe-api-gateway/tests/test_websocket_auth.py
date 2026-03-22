"""Tests for WebSocket JWT authentication."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_HOST", "localhost")


def _ws_close_code(client: TestClient, url: str) -> int:
    """
    Connect to a WebSocket endpoint and return the close code.
    Starlette's TestClient raises WebSocketDisconnect when the server closes
    the connection — we catch it and return the code.
    """
    try:
        with client.websocket_connect(url) as ws:
            ws.receive_json()  # Server should close before sending anything useful
    except WebSocketDisconnect as exc:
        return exc.code
    return 1000  # Normal close — means auth was accepted (test failure)


def test_websocket_rejects_connection_without_token():
    """WS must reject connections that don't provide a ?token= JWT."""
    from app.main import app
    job_id = str(uuid4())
    fake_job = {"id": job_id, "tenant_id": str(uuid4()), "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"


def test_websocket_rejects_invalid_token():
    """WS must reject connections with a malformed JWT."""
    from app.main import app
    job_id = str(uuid4())
    fake_job = {"id": job_id, "tenant_id": str(uuid4()), "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}?token=not-a-valid-jwt")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"


def test_websocket_rejects_wrong_tenant_token():
    """WS must reject a valid JWT whose tenant_id doesn't match the job owner."""
    import jwt as pyjwt
    from app.main import app
    job_id = str(uuid4())
    real_tenant = str(uuid4())
    other_tenant = str(uuid4())

    token = pyjwt.encode(
        {"sub": other_tenant, "tenant_id": other_tenant, "tier": "FREE", "type": "access"},
        "test-secret-key-for-testing-only",
        algorithm="HS256",
    )
    fake_job = {"id": job_id, "tenant_id": real_tenant, "status": "TRANSCRIBING"}

    with patch("app.api.routers.websocket.get_job", new_callable=AsyncMock, return_value=fake_job):
        client = TestClient(app)
        code = _ws_close_code(client, f"/ws/jobs/{job_id}?token={token}")
    assert code == 4003, f"Expected 4003 Unauthorized, got {code}"
