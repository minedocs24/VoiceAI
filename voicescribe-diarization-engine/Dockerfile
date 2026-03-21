# syntax=docker/dockerfile:1.4
# Build: docker build --secret id=hf_token,env=HUGGINGFACE_TOKEN -t voicescribe-diarization-engine .
# Il token HF non viene esposto nella history dell'immagine (mount type=secret).

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY openapi.yaml ./
COPY run.py ./

RUN pip3 install --no-cache-dir --upgrade pip && pip3 install --no-cache-dir .

# Pre-download Pyannote model in build (token via secret, non in layer history)
# Build: docker build --secret id=hf_token,env=HUGGINGFACE_TOKEN ...
COPY scripts/download_model.py /tmp/download_model.py
RUN --mount=type=secret,id=hf_token \
    python3 /tmp/download_model.py && rm /tmp/download_model.py

EXPOSE 8006
CMD ["python3", "run.py"]
