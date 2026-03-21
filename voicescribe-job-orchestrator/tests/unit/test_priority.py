"""Unit tests for Celery priority by tier."""

import pytest

from app.core.config import get_priority_for_tier


def test_free_tier_priority():
    assert get_priority_for_tier("FREE") == 1


def test_pro_tier_priority():
    assert get_priority_for_tier("PRO") == 5


def test_enterprise_tier_priority():
    assert get_priority_for_tier("ENTERPRISE") == 10


def test_case_insensitive():
    assert get_priority_for_tier("free") == 1
    assert get_priority_for_tier("Free") == 1
