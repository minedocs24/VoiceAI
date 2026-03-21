"""FFmpeg audio preprocessing pipeline."""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

from structlog import get_logger

from app.core.config import get_preprocessor_config, settings

logger = get_logger(__name__)


class PreprocessError(Exception):
    """Base exception for preprocessing errors."""

    pass


class InputError(PreprocessError):
    """Input file error - no retry."""

    pass


class SystemError(PreprocessError):
    """System/temporary error - retry with backoff."""

    pass


def build_filter_complex(
    sample_rate: int = 16000,
    channels: int = 1,
    loudness_lufs: float = -23.0,
    noise_reduction: bool = True,
) -> str:
    """Build FFmpeg filter_complex string."""
    cfg = get_preprocessor_config()
    nr_cfg = cfg.get("noise_reduction", {}).get("afftdn", {})
    nr_val = nr_cfg.get("nr", 12)
    nf_val = nr_cfg.get("nf", -25)

    # Extract audio, resample, mono (downmix if multichannel), loudnorm, optional afftdn
    # Use aresample without soxr for portability (soxr may be unavailable on some builds)
    pan_filter = "pan=mono|c0=c0" if channels == 1 else "pan=mono|c0=0.5*c0+0.5*c1"
    filters = [
        f"aresample={sample_rate}",
        pan_filter,
        f"loudnorm=I={loudness_lufs}:TP=-1.5:LRA=11.0",
    ]
    filters = [f for f in filters if f]

    if noise_reduction:
        filters.append(f"afftdn=nr={nr_val}:nf={nf_val}")

    return ",".join(filters)


def run_preprocess(
    input_path: str,
    output_path: str,
    timeout_seconds: int | None = None,
) -> str:
    """
    Run FFmpeg preprocessing pipeline.
    Returns SHA-256 hex of output file.
    Raises InputError for non-retryable, SystemError for retryable.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise InputError(f"Input file not found: {input_path}")

    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)

    cfg = get_preprocessor_config()
    sample_rate = cfg.get("output", {}).get("sample_rate", 16000)
    channels = cfg.get("output", {}).get("channels", 1)
    loudness = cfg.get("loudness", {}).get("target_lufs", -23.0)
    nr_enabled = cfg.get("noise_reduction", {}).get("enabled", True)
    timeout = timeout_seconds or cfg.get("ffmpeg", {}).get("timeout_seconds", 120)
    threads = cfg.get("ffmpeg", {}).get("threads", 0)

    filter_complex = build_filter_complex(
        sample_rate=sample_rate,
        channels=channels,
        loudness_lufs=loudness,
        noise_reduction=nr_enabled,
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-threads",
        str(threads),
        "-i",
        str(input_p),
        "-af",
        filter_complex,
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(output_p),
    ]

    logger.info("ffmpeg_start", input=str(input_p), output=str(output_p))
    start = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise SystemError(f"FFmpeg timeout after {timeout}s")
    except OSError as e:
        if "No such file" in str(e) or "ffmpeg" in str(e).lower():
            raise InputError("FFmpeg not found or not executable")
        raise SystemError(f"FFmpeg execution failed: {e}")

    elapsed = time.perf_counter() - start
    logger.info("ffmpeg_done", elapsed_seconds=round(elapsed, 2), returncode=result.returncode)

    if result.returncode != 0:
        stderr = result.stderr or ""
        # Input errors: clear indicators of bad/corrupt input
        if "Invalid data" in stderr or "does not contain any stream" in stderr:
            raise InputError(f"Invalid or unsupported input: {stderr[-500:]}")
        if "No space left" in stderr or "ENOSPC" in stderr:
            raise SystemError("Ramdisk full")
        # Use last part of stderr for error (FFmpeg prints version first)
        err_snippet = stderr[-500:] if len(stderr) > 500 else stderr
        raise SystemError(f"FFmpeg failed (code {result.returncode}): {err_snippet}")

    if not output_p.exists():
        raise SystemError("Output file was not created")

    sha256 = hashlib.sha256()
    with open(output_p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
