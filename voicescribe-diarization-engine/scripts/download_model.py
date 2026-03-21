#!/usr/bin/env python3
"""Download Pyannote model at build time. Legge token da /run/secrets/hf_token."""
import sys
from pathlib import Path

def main():
    secret_path = Path("/run/secrets/hf_token")
    if not secret_path.exists():
        print("Secret hf_token not mounted. Skip model download.", file=sys.stderr)
        sys.exit(0)
    token = secret_path.read_text().strip()
    if not token:
        print("Empty token. Skip model download.", file=sys.stderr)
        sys.exit(0)
    model_name = "pyannote/speaker-diarization-3.1"
    cache_dir = Path("/models/pyannote")
    cache_dir.mkdir(parents=True, exist_ok=True)
    from pyannote.audio import Pipeline
    Pipeline.from_pretrained(model_name, use_auth_token=token, cache_dir=str(cache_dir))
    print("Model downloaded.", file=sys.stderr)

if __name__ == "__main__":
    main()
