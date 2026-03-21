"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_gpu_state_after_test():
    """Opzionale: reset stato GPU dopo test che lo modificano."""
    yield
    # I test unit che mockano lo stato non dipendono da cleanup globale
