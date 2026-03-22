"""Unit tests for state machine."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.state_machine import get_next_stage_for_tier, validate_transition


def test_valid_transition_queued_to_preprocessing():
    assert validate_transition("QUEUED", "PREPROCESSING") is True


def test_valid_transition_preprocessing_to_transcribing():
    assert validate_transition("PREPROCESSING", "TRANSCRIBING") is True


def test_invalid_transition_queued_to_done():
    assert validate_transition("QUEUED", "DONE") is False


def test_invalid_transition_done_to_anything():
    assert validate_transition("DONE", "FAILED") is False


def test_free_tier_skips_diarization():
    assert get_next_stage_for_tier("TRANSCRIBING", "FREE") == "EXPORTING"


def test_pro_tier_goes_to_diarization():
    assert get_next_stage_for_tier("TRANSCRIBING", "PRO") == "DIARIZING"


def test_enterprise_tier_goes_to_diarization():
    assert get_next_stage_for_tier("TRANSCRIBING", "ENTERPRISE") == "DIARIZING"


def test_failed_to_queued_for_retry():
    assert validate_transition("FAILED", "QUEUED") is True


@pytest.mark.asyncio
async def test_transition_job_serializes_history_as_json():
    """
    transition_job must pass json.dumps(history) to conn.execute, not the raw list.
    asyncpg cannot serialize a Python list to ::jsonb without explicit json.dumps().
    """
    job_id = uuid4()
    existing_history = [
        {"from": "QUEUED", "to": "PREPROCESSING", "at": "2026-01-01T00:00:00+00:00", "stage_duration_seconds": None}
    ]

    mock_row = {"id": job_id, "status": "PREPROCESSING", "status_history": existing_history}
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=mock_row)
    mock_conn.execute = AsyncMock()

    # Mock the async context manager for transaction
    mock_tx = AsyncMock()
    mock_tx.__aenter__ = AsyncMock(return_value=None)
    mock_tx.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    # Mock pool.acquire() as async context manager
    mock_acquire = AsyncMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=False)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire)

    with patch("app.core.database.get_pool", return_value=mock_pool):
        from app.core.database import transition_job
        result = await transition_job(job_id, "PREPROCESSING", "TRANSCRIBING")

    assert result is True
    call_args = mock_conn.execute.call_args
    # conn.execute(sql, *params) → call_args[0] = (sql, job_id, to_status, history, ...)
    # index 0=sql, 1=job_id($1), 2=to_status($2), 3=history($3)
    positional = call_args[0]
    history_param = positional[3]
    assert isinstance(history_param, str), (
        f"Expected str (JSON) for history param, got {type(history_param)}: {history_param!r}"
    )
    parsed = json.loads(history_param)
    assert len(parsed) == 2  # existing entry + new entry appended
    assert parsed[-1]["from"] == "PREPROCESSING"
    assert parsed[-1]["to"] == "TRANSCRIBING"
