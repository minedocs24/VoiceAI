from __future__ import annotations

import pytest

from app.services.transcription import CudaDeviceError, CudaOOMError, _run_inference_with_cuda_recovery


class FailModel:
    def __init__(self, message: str):
        self.message = message

    def transcribe(self, *_args, **_kwargs):
        raise RuntimeError(self.message)


def test_cuda_oom_raises_after_retry(monkeypatch):
    model = FailModel("CUDA out of memory")
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(CudaOOMError):
        _run_inference_with_cuda_recovery(model, "fake.wav", beam_size=5)


def test_cuda_device_error_is_not_retried():
    model = FailModel("CUDA driver device assert")

    with pytest.raises(CudaDeviceError):
        _run_inference_with_cuda_recovery(model, "fake.wav", beam_size=5)
