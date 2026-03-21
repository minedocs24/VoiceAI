"""Unit tests for state machine."""

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
