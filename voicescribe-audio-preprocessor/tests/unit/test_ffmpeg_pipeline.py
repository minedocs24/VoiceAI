"""Unit tests for FFmpeg pipeline."""

from pathlib import Path

import pytest

from app.services.ffmpeg_pipeline import (
    InputError,
    SystemError,
    build_filter_complex,
    run_preprocess,
)


def test_build_filter_complex_default():
    """Filter complex includes resample, mono, loudnorm."""
    fc = build_filter_complex(sample_rate=16000, channels=1, loudness_lufs=-23.0, noise_reduction=True)
    assert "aresample=16000" in fc
    assert "loudnorm" in fc
    assert "afftdn" in fc


def test_build_filter_complex_no_noise_reduction():
    """Without noise reduction, afftdn is excluded."""
    fc = build_filter_complex(noise_reduction=False)
    assert "afftdn" not in fc


def test_run_preprocess_file_not_found(tmp_path):
    """Missing input raises InputError."""
    with pytest.raises(InputError, match="not found"):
        run_preprocess(
            str(tmp_path / "nonexistent.wav"),
            str(tmp_path / "out.wav"),
        )


def test_run_preprocess_success(sample_wav, tmp_path):
    """Valid WAV is processed and output has SHA-256."""
    out = tmp_path / "ramdisk" / "job-123.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    sha = run_preprocess(sample_wav, str(out), timeout_seconds=30)
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)
    assert out.exists()
    assert out.stat().st_size > 0
