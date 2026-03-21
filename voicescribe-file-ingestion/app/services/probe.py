"""FFmpeg/ffprobe metadata extraction with timeout."""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_ingestion_config, settings
from app.core.metrics import PROBE_DURATION_SECONDS
from app.core.redis_client import get_json_cache, set_json_cache


def ffmpeg_available() -> bool:
    """Return True if ffprobe is available in PATH."""
    return shutil.which("ffprobe") is not None or shutil.which("ffmpeg") is not None


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def probe_media_file(job_id: str, file_path: str) -> dict:
    """Probe media metadata and cache by job_id."""
    cache_key = f"probe:{job_id}"
    ttl = int(get_ingestion_config().get("probe_cache_ttl_seconds", settings.probe_cache_ttl_seconds))
    timeout = int(get_ingestion_config().get("probe_timeout_seconds", settings.probe_timeout_seconds))

    cached = await get_json_cache(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found for job")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        file_path,
    ]

    start = time.perf_counter()
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=503, detail="Probe timeout") from exc
    finally:
        PROBE_DURATION_SECONDS.observe(time.perf_counter() - start)

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="ignore")[:300]
        raise HTTPException(status_code=422, detail=f"Probe failed: {detail}")

    try:
        parsed = json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Invalid ffprobe output") from exc

    streams = parsed.get("streams", [])
    format_info = parsed.get("format", {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration = float(format_info.get("duration", 0.0) or 0.0)
    payload = {
        "job_id": job_id,
        "duration_seconds": duration,
        "audio_codec": audio_stream.get("codec_name"),
        "sample_rate": _to_int(audio_stream.get("sample_rate")),
        "channels": _to_int(audio_stream.get("channels")),
        "bitrate": _to_int(format_info.get("bit_rate")),
        "cached": False,
    }

    await set_json_cache(cache_key, payload, ttl)
    return payload