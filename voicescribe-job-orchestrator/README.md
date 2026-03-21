# VoiceScribe Job Orchestrator (SVC-05)

Orchestratore della pipeline di trascrizione. Gestisce la state machine dei job, invia task ai servizi downstream e riceve callback.

## State machine

QUEUED → PREPROCESSING → TRANSCRIBING → [DIARIZING] → EXPORTING → DONE  
(Free Tier salta DIARIZING)  
Qualsiasi stato → FAILED  
FAILED → QUEUED (retry)

## Features

- Creazione job e dispatch a SVC-04
- Callback da SVC-04, SVC-06, SVC-07, SVC-08
- Circuit breaker e retry con tenacity
- Rollback best-effort su fallimento
- Publish Redis `job:{id}:status` a completamento
- Metriche Prometheus

## Configurazione

1. Copia `.env.example` in `.env`
2. Configura `DATABASE_URL`, `REDIS_*`, URL servizi, `INTERNAL_SERVICE_TOKEN`

## Avvio

```bash
python run.py
```

## Endpoint

- `POST /jobs` — crea job
- `GET /jobs/{job_id}` — stato job
- `POST /jobs/{job_id}/retry` — retry job fallito
- `POST /jobs/{job_id}/cancel` — cancella job
- `GET /queue/stats` — statistiche code
- `POST /callbacks/preprocessing-complete` — callback SVC-04
- `POST /callbacks/transcription-complete` — callback SVC-06
- `POST /callbacks/diarization-complete` — callback SVC-07
- `POST /callbacks/export-complete` — callback SVC-08
