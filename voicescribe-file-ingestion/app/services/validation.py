"""File extension and magic-bytes validation."""

from __future__ import annotations

from fastapi import HTTPException

from app.core.config import get_ingestion_config, settings


def extract_extension(filename: str | None) -> str:
    """Extract lowercase extension without dot."""
    if not filename or "." not in filename:
        raise HTTPException(status_code=400, detail="Missing or invalid filename extension")
    ext = filename.rsplit(".", 1)[-1].strip().lower()
    if not ext:
        raise HTTPException(status_code=400, detail="Missing filename extension")
    return ext


def _parse_signature(signature: str) -> list[int | None]:
    parts = signature.split()
    parsed: list[int | None] = []
    for part in parts:
        if part == "??":
            parsed.append(None)
        else:
            parsed.append(int(part, 16))
    return parsed


def _matches_signature(prefix: bytes, signature: str) -> bool:
    sig = _parse_signature(signature)
    if len(prefix) < len(sig):
        return False
    for idx, value in enumerate(sig):
        if value is None:
            continue
        if prefix[idx] != value:
            return False
    return True


def get_allowed_formats() -> dict:
    """Load configured format signatures."""
    cfg = get_ingestion_config()
    return cfg.get("formats", {})


def validate_extension(filename_ext: str) -> None:
    """Reject if extension is not in whitelist."""
    allowed = get_allowed_formats()
    if filename_ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported extension: {filename_ext}")


def detect_format_from_magic(prefix_bytes: bytes) -> str:
    """Detect trusted extension from magic bytes signatures."""
    allowed = get_allowed_formats()
    for ext, meta in allowed.items():
        signatures = meta.get("magic_bytes", [])
        for signature in signatures:
            if _matches_signature(prefix_bytes, signature):
                if ext == "m4a":
                    return "m4a"
                if ext in {"webm", "mkv"}:
                    return ext
                return ext
    raise HTTPException(status_code=400, detail="Magic bytes validation failed")


def ensure_extension_coherent(declared_ext: str, detected_ext: str) -> None:
    """Allow known container overlap but reject obvious mismatch."""
    if declared_ext == detected_ext:
        return
    # Containers can overlap: mp4 and m4a share ftyp; mkv and webm share EBML
    allowed_pairs = {
        ("mp4", "m4a"),
        ("m4a", "mp4"),
        ("mkv", "webm"),
        ("webm", "mkv"),
    }
    if (declared_ext, detected_ext) in allowed_pairs:
        return
    raise HTTPException(
        status_code=400,
        detail=(
            f"Declared extension '{declared_ext}' does not match detected format '{detected_ext}'"
        ),
    )


def magic_buffer_size() -> int:
    """Configured max bytes to inspect for signatures."""
    cfg = get_ingestion_config()
    return int(cfg.get("magic_buffer_size", settings.magic_buffer_size))