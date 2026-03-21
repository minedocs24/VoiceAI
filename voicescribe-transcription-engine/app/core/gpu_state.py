"""Process-wide GPU/model runtime state."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class RuntimeState:
    model_name: str = ""
    compute_type: str = ""
    cuda_version: str = ""
    ready: bool = False
    busy: bool = False
    last_rtf: float = 0.0
    model_vram_used_mb: float = 0.0
    last_error: str | None = None


runtime_state = RuntimeState()
state_lock = threading.Lock()
model_lock = threading.Lock()
loaded_model = None


def set_busy(value: bool) -> None:
    with state_lock:
        runtime_state.busy = value


def update_last_rtf(value: float) -> None:
    with state_lock:
        runtime_state.last_rtf = value
