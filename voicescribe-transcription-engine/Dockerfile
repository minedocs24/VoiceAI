FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends     python3 python3-pip ffmpeg ca-certificates &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY openapi.yaml ./openapi.yaml
COPY run.py ./run.py

RUN pip3 install --no-cache-dir --upgrade pip &&     pip3 install --no-cache-dir .

# Pre-download whisper model to make image self-contained.
ARG WHISPER_MODEL=large-v3
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/models/whisper')"

EXPOSE 8005
CMD ["python3", "run.py"]
