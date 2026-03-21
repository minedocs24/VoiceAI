from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.validation import detect_format_from_magic
from app.services.storage import build_final_path


def test_detect_magic_bytes_mp3_id3():
    prefix = bytes.fromhex("49 44 33 04 00 00")
    assert detect_format_from_magic(prefix) == "mp3"


def test_detect_magic_bytes_reject_png_renamed_mp3():
    prefix = bytes.fromhex("89 50 4E 47 0D 0A 1A 0A")
    with pytest.raises(HTTPException):
        detect_format_from_magic(prefix)


def test_build_final_path_pattern_contains_components():
    file_uuid, path = build_final_path("/data/input", "tenant-1", "11111111-1111-1111-1111-111111111111", "mp3")
    assert "tenant-1" in path
    assert "11111111-1111-1111-1111-111111111111" in path
    assert path.endswith(".mp3")
    assert len(file_uuid) == 36