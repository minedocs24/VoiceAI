"""Test fallback: servizio in modalità degradata risponde 503."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client_degraded():
    """Client con modello non caricato (simula token invalido)."""
    from app.core import gpu_state

    def _no_load(_force=False):
        gpu_state.runtime_state.ready = False
        gpu_state.runtime_state.hf_token_valid = False
        gpu_state.runtime_state.last_error = "HuggingFace token invalid or model unavailable"
        return None

    with patch("app.main.load_model_once", side_effect=_no_load):
        app = create_app()
        client = TestClient(app)
        gpu_state.runtime_state.ready = False
        gpu_state.runtime_state.hf_token_valid = False
        yield client


def test_diarize_returns_503_when_not_ready(client_degraded):
    """POST /diarize con modello non caricato restituisce 503."""
    resp = client_degraded.post(
        "/diarize",
        json={"job_id": "00000000-0000-0000-0000-000000000001", "input_path": "/tmp/any.wav"},
        headers={"X-Internal-Token": "test"},
    )
    assert resp.status_code == 503
    data = resp.json()
    assert "detail" in data
    assert "unavailable" in data["detail"].lower() or "token" in data["detail"].lower()


def test_models_status_shows_not_ready(client_degraded):
    """GET /models/status con servizio degradato mostra model_loaded=false."""
    resp = client_degraded.get("/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_loaded"] is False
    assert data["service_ready"] is False
    assert "hf_token_valid" in data
