# VoiceScribe Audio Preprocessor (SVC-04)

Servizio di pre-processing audio per la pipeline VoiceScribe. Converte file audio in input in WAV 16kHz mono con normalizzazione EBU R128 e riduzione rumore per la trascrizione GPU.

## Features

- Pipeline FFmpeg: estrazione audio → resample → mono → loudnorm → afftdn (opzionale)
- Output su Ramdisk: `{job_id}.wav`. SHA-256 calcolato post-processing
- Guardia quota secondaria: check SVC-03 prima di elaborare
- Task Celery con `task_acks_late=True` su coda `cpu_tasks`
- Gestione errori: input (no retry), sistema (retry 30s/90s/270s), notifica (retry solo callback)
- Endpoint HTTP: `POST /preprocess`, `GET /preprocess/{task_id}/status`, `GET /formats`

## Configurazione

1. Copia `.env.example` in `.env`
2. Configura: `CELERY_BROKER_URL`, `RAMDISK_PATH`, `STORAGE_BASE_PATH`, `SVC02_URL`, `SVC05_URL`, `SVC03_URL`, `INTERNAL_SERVICE_TOKEN`
3. Adatta `config/preprocessor.yml` per parametri FFmpeg

## Avvio

```bash
# HTTP API
python run.py

# Celery worker
celery -A app.celery_app worker -Q cpu_tasks -c 12 --loglevel=info
```

## Docker

```bash
docker build -t voicescribe-audio-preprocessor .
docker run --rm -p 8003:8003 -v /mnt/ramdisk:/mnt/ramdisk -v /data/input:/data/input voicescribe-audio-preprocessor
```

## Endpoint

- `POST /preprocess` — accoda task (body: job_id, tenant_id, input_path opzionale)
- `GET /preprocess/{task_id}/status` — stato task Celery
- `GET /formats` — formati supportati
- `GET /health` — health check
- `GET /metrics` — Prometheus
