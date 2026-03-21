"""Process-wide GPU/model runtime state."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class RuntimeState:
    model_name: str = ""
    ready: bool = False
    busy: bool = False
    model_vram_used_mb: float = 0.0
    load_seconds: float = 0.0
    last_error: str | None = None
    hf_token_valid: bool = False


runtime_state = RuntimeState()
state_lock = threading.Lock()
model_lock = threading.Lock()
loaded_model = None


def set_busy(value: bool) -> None:
    with state_lock:
        runtime_state.busy = value
