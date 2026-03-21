"""Integration tests for preprocessing (requires Redis, FFmpeg)."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.services.ffmpeg_pipeline import run_preprocess


@pytest.fixture
def sample_wav(tmp_path):
    """Minimal WAV file."""
    import wave

    p = tmp_path / "input" / "test.wav"
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 4410)
    return str(p)


def test_preprocess_produces_valid_wav(sample_wav, tmp_path):
    """Preprocessing produces valid WAV with correct properties."""
    out_dir = tmp_path / "ramdisk"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "job-abc.wav"

    sha = run_preprocess(sample_wav, str(out_path), timeout_seconds=30)

    assert out_path.exists()
    assert len(sha) == 64
    # Verify it's valid WAV (RIFF header)
    with open(out_path, "rb") as f:
        header = f.read(12)
    assert header[:4] == b"RIFF"
    assert header[8:12] == b"WAVE"


def test_parallel_preprocess_no_race_condition(sample_wav, tmp_path):
    """12 parallel preprocessing tasks with unique job_ids produce distinct output files without race."""
    import concurrent.futures

    out_dir = tmp_path / "ramdisk"
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = [out_dir / f"job-{i:02d}.wav" for i in range(12)]

    def run_one(i: int) -> str:
        return run_preprocess(sample_wav, str(outputs[i]), timeout_seconds=30)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        shas = list(ex.map(run_one, range(12)))

    # All outputs exist and are distinct (different SHA for same input processed to same spec = same SHA, but paths differ)
    for i, out in enumerate(outputs):
        assert out.exists(), f"Output {i} missing"
    # All SHAs should be identical (same input, same pipeline) - verifies no corruption
    assert len(set(shas)) == 1
    # All files have same size (same processing)
    sizes = [p.stat().st_size for p in outputs]
    assert len(set(sizes)) == 1
