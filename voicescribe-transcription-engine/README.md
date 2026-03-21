# VoiceScribe Transcription Engine (SVC-06)

Servizio standalone per trascrizione speech-to-text basato su Faster-Whisper.

## Obiettivo

Fornire un motore di trascrizione riutilizzabile in qualsiasi progetto, indipendente da VoiceScribe AI.

## Endpoint principali

- `POST /transcribe` trascrizione sincrona
- `POST /transcribe/async` trascrizione asincrona via Celery
- `GET /tasks/{task_id}/status` stato task
- `GET /models` modelli supportati
- `GET /gpu/status` telemetria GPU real-time
- `GET /health` health
- `GET /metrics` metriche Prometheus

## RTF

`rtf = inference_time_seconds / audio_duration_seconds`

- `< 1.0`: pi? veloce del tempo reale
- `0.05`: target prestazionale su RTX 6000 per file brevi

## Avvio rapido standalone

1. Copia `.env.example` in `.env`
2. Configura almeno `INTERNAL_SERVICE_TOKEN` e `SVC05_URL` (se usi callback)
3. Avvia API:

```bash
python run.py
```

4. Avvia worker GPU:

```bash
celery -A app.celery_app worker -Q gpu_tasks -c 1 --loglevel=info
```

## Docker

- `Dockerfile` (GPU/CUDA)
- `Dockerfile.cpu` (test/dev senza GPU)

## Benchmark

Per benchmark consistenti:
- usa audio italiano 20-30s in `tests/fixtures/`
- esegui pi? run e calcola p50/p95 di latenza e RTF
- monitora `/gpu/status` e `/metrics`
