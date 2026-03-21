"""Unit tests for export service tier logic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.export_service import TIER_FORMATS, run_export


def test_tier_free_only_txt_srt(temp_output_dir, sample_transcript):
    with patch("app.services.export_service.settings") as m:
        m.output_base_path = str(temp_output_dir)
        m.enable_txt = True
        m.enable_srt = True
        m.enable_json = False
        m.enable_docx = False
        m.download_base_url = ""

        urls, files = run_export(
            job_id="job-1",
            tenant_id="t1",
            tier="FREE",
            transcript_data=sample_transcript.model_dump(mode="json"),
            formats_requested=["txt", "srt"],
        )
        assert "txt" in urls
        assert "srt" in urls
        assert "json" not in urls
        assert "docx" not in urls
        assert len(files) == 2


def test_tier_forbidden_free_docx(temp_output_dir, sample_transcript):
    with patch("app.services.export_service.settings") as m:
        m.output_base_path = str(temp_output_dir)
        m.enable_docx = True

        with pytest.raises(ValueError, match="TIER_FORBIDDEN"):
            run_export(
                job_id="job-1",
                tenant_id="t1",
                tier="FREE",
                transcript_data=sample_transcript.model_dump(mode="json"),
                formats_requested=["docx"],
            )


def test_tier_pro_all_formats(temp_output_dir, sample_diarization):
    with patch("app.services.export_service.settings") as m:
        m.output_base_path = str(temp_output_dir)
        m.enable_txt = True
        m.enable_srt = True
        m.enable_json = True
        m.enable_docx = True
        m.download_base_url = ""

        urls, files = run_export(
            job_id="job-1",
            tenant_id="t1",
            tier="PRO",
            transcript_data=sample_diarization.model_dump(mode="json"),
            formats_requested=["txt", "srt", "json", "docx"],
        )
        assert "txt" in urls
        assert "srt" in urls
        assert "json" in urls
        assert "docx" in urls
        assert len(files) == 4
