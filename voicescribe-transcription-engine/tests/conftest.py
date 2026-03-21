from __future__ import annotations

from pathlib import Path

import pytest

from app.core import gpu_state


class DummyWord:
    def __init__(self, word: str, start: float, end: float, probability: float):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability


class DummySegment:
    def __init__(self, start: float, end: float, text: str, words: list[DummyWord], avg_logprob: float = -0.2):
        self.start = start
        self.end = end
        self.text = text
        self.words = words
        self.avg_logprob = avg_logprob


class DummyInfo:
    def __init__(self, language: str = "it"):
        self.language = language


class DummyModel:
    def __init__(self, segments=None, fail=None):
        self._segments = segments or []
        self._fail = fail

    def transcribe(self, *_args, **_kwargs):
        if self._fail:
            raise RuntimeError(self._fail)
        return self._segments, DummyInfo("it")


@pytest.fixture(autouse=True)
def reset_runtime_state(tmp_path):
    gpu_state.runtime_state.ready = True
    gpu_state.runtime_state.busy = False
    gpu_state.runtime_state.last_rtf = 0.0
    gpu_state.runtime_state.last_error = None
    gpu_state.loaded_model = None

    audio = tmp_path / "sample.wav"
    _create_wav(audio, duration_s=2.0)
    return {"audio_path": str(audio)}


def _create_wav(path: Path, duration_s: float) -> None:
    import wave

    rate = 16000
    total_frames = int(duration_s * rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * total_frames)
