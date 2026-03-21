import os
import time

from app.core.config import settings
from app.services.cleanup import cleanup_temp_files_once


def test_cleanup_temp_files(tmp_path):
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    old_file = temp_dir / "old.tmp"
    old_file.write_bytes(b"old")

    recent_file = temp_dir / "recent.tmp"
    recent_file.write_bytes(b"recent")

    old_ts = time.time() - 7200
    os.utime(old_file, (old_ts, old_ts))

    settings.temp_upload_dir = str(temp_dir)

    removed = cleanup_temp_files_once()

    assert removed >= 1
    assert not old_file.exists()
    assert recent_file.exists()