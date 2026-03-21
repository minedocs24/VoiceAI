"""Pytest fixtures and configuration."""

import os

import pytest


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set minimal env for tests."""
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-internal-token")
    monkeypatch.setenv("FREE_TIER_DAILY_LIMIT", "2")
