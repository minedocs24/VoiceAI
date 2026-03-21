import hashlib
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.services.storage import stream_to_temp


@pytest.mark.asyncio
async def test_streaming_sha256(tmp_path):
    settings.temp_upload_dir = str(tmp_path)

    content = b"abc" * 1024
    expected = hashlib.sha256(content).hexdigest()

    upload = UploadFile(filename="test.mp3", file=BytesIO(content))
    result = await stream_to_temp(upload)

    assert result.size_bytes == len(content)
    assert result.sha256 == expected
    assert result.temp_path.exists()