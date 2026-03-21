"""Audio helper utilities."""

from __future__ import annotations

import contextlib
import subprocess
import tempfile
import wave
from pathlib import Path


def get_audio_duration_seconds(path: str) -> float:
    audio_path = Path(path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    with contextlib.suppress(wave.Error):
        with wave.open(str(audio_path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if rate > 0:
                return float(frames) / float(rate)

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def extract_audio_chunk(input_path: str, start_s: float, duration_s: float) -> str:
    temp_dir = Path(tempfile.mkdtemp(prefix="svc06_chunk_"))
    output_path = temp_dir / "chunk.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_s),
            "-t",
            str(duration_s),
            "-i",
            input_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return str(output_path)
