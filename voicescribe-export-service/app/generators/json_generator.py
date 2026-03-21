"""JSON format generator - serialization with metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Union

from app.models.schemas import DiarizationResult, TranscriptResult

ExportInput = Union[TranscriptResult, DiarizationResult]


class JsonGenerator:
    """Produces transcript.json with job metadata."""

    def generate(
        self,
        data: ExportInput,
        *,
        job_id: str,
        tenant_id: str,
        tier: str,
        processed_at: str | None = None,
    ) -> str:
        """Serialize data with metadata. Pretty-print indent 2."""
        base = data.model_dump(mode="json")
        base["job_id"] = job_id
        base["tenant_id"] = tenant_id
        base["tier"] = tier
        base["processed_at"] = processed_at or datetime.now(timezone.utc).isoformat()
        base["rtf"] = data.rtf
        base["inference_ms"] = data.inference_ms
        import json
        return json.dumps(base, indent=2, ensure_ascii=False)
