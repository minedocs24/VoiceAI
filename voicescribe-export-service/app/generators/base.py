"""Base types for generators."""

from __future__ import annotations

from typing import Protocol, Union

from app.models.schemas import DiarizationResult, TranscriptResult


ExportInput = Union[TranscriptResult, DiarizationResult]


class BaseGenerator(Protocol):
    """Protocol for format generators."""

    def generate(self, data: ExportInput, **kwargs: object) -> str | bytes:
        """Generate content. Returns str for text formats, bytes for binary (DOCX)."""
        ...
