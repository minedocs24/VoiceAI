"""Export service - orchestration of generators and file writing."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from structlog import get_logger

from app.core.config import load_export_config, settings
from app.generators import DocxGenerator, JsonGenerator, SrtGenerator, TxtGenerator
from app.models.schemas import DiarizationResult, TranscriptResult

logger = get_logger(__name__)

TIER_FORMATS = {
    "FREE": ["txt", "srt"],
    "PRO": ["txt", "srt", "json", "docx"],
    "ENTERPRISE": ["txt", "srt", "json", "docx"],
}


def _parse_transcript(data: dict[str, Any]) -> TranscriptResult | DiarizationResult:
    """Parse dict into TranscriptResult or DiarizationResult."""
    if "speakers" in data and data["speakers"]:
        return DiarizationResult.model_validate(data)
    return TranscriptResult.model_validate(data)


def _get_output_dir(tenant_id: str, job_id: str) -> Path:
    """Build output directory path."""
    base = Path(settings.output_base_path)
    out = base / tenant_id / job_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def _build_download_url(tenant_id: str, job_id: str, filename: str) -> str:
    """Build download URL if base URL configured."""
    if not settings.download_base_url:
        return ""
    base = settings.download_base_url.rstrip("/")
    return f"{base}/{tenant_id}/{job_id}/{filename}"


def run_export(
    job_id: str,
    tenant_id: str,
    tier: str,
    transcript_data: dict[str, Any],
    *,
    include_timestamps_txt: bool = False,
    formats_requested: list[str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """
    Run export for given tier. Returns (download_urls, files_created).
    Raises ValueError for TIER_FORBIDDEN if a requested format is not allowed.
    """
    cfg = load_export_config()
    filenames = cfg.get("output", {}).get("filenames", {})
    allowed = TIER_FORMATS.get(tier.upper(), TIER_FORMATS["FREE"])
    formats_to_generate = formats_requested or allowed

    for fmt in formats_to_generate:
        if fmt.lower() not in [a.lower() for a in allowed]:
            raise ValueError("TIER_FORBIDDEN")

    # Filter by enabled formats in settings
    enabled = []
    if settings.enable_txt and "txt" in [f.lower() for f in formats_to_generate]:
        enabled.append("txt")
    if settings.enable_srt and "srt" in [f.lower() for f in formats_to_generate]:
        enabled.append("srt")
    if settings.enable_json and "json" in [f.lower() for f in formats_to_generate]:
        enabled.append("json")
    if settings.enable_docx and "docx" in [f.lower() for f in formats_to_generate]:
        enabled.append("docx")

    data = _parse_transcript(transcript_data)
    out_dir = _get_output_dir(tenant_id, job_id)
    download_urls: dict[str, str] = {}
    files_created: list[str] = []

    srt_cfg = cfg.get("srt", {})
    srt_gen = SrtGenerator(
        max_chars_per_line=srt_cfg.get("max_chars_per_line", 80),
        max_duration_seconds=float(srt_cfg.get("max_duration_seconds", 3.0)),
    )

    if "txt" in enabled:
        txt_gen = TxtGenerator()
        content = txt_gen.generate(data, include_timestamps=include_timestamps_txt)
        fname = filenames.get("txt", "transcript.txt")
        path = out_dir / fname
        path.write_text(content, encoding="utf-8")
        files_created.append(str(path))
        download_urls["txt"] = _build_download_url(tenant_id, job_id, fname)

    if "srt" in enabled:
        content = srt_gen.generate(data)
        fname = filenames.get("srt", "transcript.srt")
        path = out_dir / fname
        path.write_text(content, encoding="utf-8")
        files_created.append(str(path))
        url = _build_download_url(tenant_id, job_id, fname)
        if url:
            download_urls["srt"] = url

    if "json" in enabled:
        json_gen = JsonGenerator()
        content = json_gen.generate(
            data,
            job_id=job_id,
            tenant_id=tenant_id,
            tier=tier,
        )
        fname = filenames.get("json", "transcript.json")
        path = out_dir / fname
        path.write_text(content, encoding="utf-8")
        files_created.append(str(path))
        download_urls["json"] = _build_download_url(tenant_id, job_id, fname)

    if "docx" in enabled:
        docx_gen = DocxGenerator()
        duration_str = f"{data.duration:.1f}s" if data.duration else None
        model_str = f"RTF={data.rtf}" if data.rtf else None
        content = docx_gen.generate(
            data,
            job_id=job_id,
            tenant_id=tenant_id,
            project_name=f"Job {job_id}",
            duration_str=duration_str,
            model_str=model_str,
        )
        fname = filenames.get("docx", "transcript.docx")
        path = out_dir / fname
        path.write_bytes(content)
        files_created.append(str(path))
        download_urls["docx"] = _build_download_url(tenant_id, job_id, fname)

    return download_urls, files_created
