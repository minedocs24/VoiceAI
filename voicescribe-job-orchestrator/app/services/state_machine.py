"""Job state machine validation."""

from __future__ import annotations

from app.core.config import get_valid_transitions


def validate_transition(from_status: str, to_status: str) -> bool:
    """Check if transition is valid. Returns True if allowed."""
    transitions = get_valid_transitions()
    allowed = transitions.get(from_status, [])
    return to_status in allowed


def get_next_stage_for_tier(current: str, tier: str) -> str | None:
    """
    Get next stage after transcription.
    FREE: TRANSCRIBING -> EXPORTING (skip DIARIZING)
    PRO/ENTERPRISE: TRANSCRIBING -> DIARIZING
    """
    if current == "TRANSCRIBING":
        return "EXPORTING" if tier.upper() == "FREE" else "DIARIZING"
    return None
