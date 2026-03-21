# VoiceScribe Export Service (SVC-08)

Servizio standalone per la generazione di documenti a partire da dati strutturati con segmenti temporali e testo. Trasforma output di trascrizione e diarizzazione in formati leggibili: TXT, SRT, JSON, DOCX.

## Obiettivo

Fornire un servizio di export riutilizzabile in qualsiasi progetto che richieda generazione di report o documenti da dati con timestamp: pipeline di trascrizione, meeting recorder, call center, report automatici.

## Formati supportati

| Formato | Tier   | Descrizione                          |
|---------|--------|--------------------------------------|
| TXT     | Tutti  | Testo plain, con/senza speaker       |
| SRT     | Tutti  | Sottotitoli compatibili VLC/YouTube  |
| JSON    | PRO+   | Serializzazione arricchita con metadata |
| DOCX    | PRO+   | Documento Word con speaker colorati  |

## Avvio rapido standalone

1. Copia `.env.example` in `.env`
2. Configura `OUTPUT_BASE_PATH`, `RAMDISK_PATH`, `REDIS_URL`, `SVC05_CALLBACK_URL`, `INTERNAL_SERVICE_TOKEN`
3. Avvia API:

```bash
pip install -e .[dev]
python run.py
```

4. Worker Celery (coda `export_tasks`):

```bash
celery -A app.celery_app worker -Q export_tasks -c 2 --loglevel=info
```

5. Beat per cleanup notturno (opzionale):

```bash
celery -A app.celery_app beat --loglevel=info
```

## Esempio: generare documenti da dati strutturati

```bash
curl -X POST http://localhost:8007/export \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: your_token" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "tenant1",
    "tier": "PRO",
    "transcript": {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "language": "it",
      "duration": 120.5,
      "rtf": 0.05,
      "inference_ms": 6000,
      "segments": [
        {"start": 0.0, "end": 2.5, "text": "Buongiorno a tutti.", "speaker": "SPEAKER_00"},
        {"start": 2.5, "end": 5.0, "text": "Grazie per essere qui.", "speaker": "SPEAKER_01"}
      ]
    },
    "formats": ["txt", "srt", "docx"]
  }'
```

Risposta:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "files": ["/data/output/tenant1/550e8400.../transcript.txt", "..."],
  "download_urls": {
    "txt": "tenant1/550e8400.../transcript.txt",
    "srt": "tenant1/550e8400.../transcript.srt",
    "docx": "tenant1/550e8400.../transcript.docx"
  }
}
```

## Endpoint

- `POST /export` — genera documenti
- `DELETE /cleanup/{job_id}` — elimina WAV dal Ramdisk
- `POST /webhook/notify` — invia notifica webhook (uso interno)
- `GET /health` — health check
- `GET /metrics` — Prometheus

## Docker

```bash
docker build -t voicescribe-export-service .
docker run --rm -p 8007:8007 \
  -v /data/output:/data/output \
  -v /mnt/ramdisk:/mnt/ramdisk \
  voicescribe-export-service
```

## Documentazione

- [docs/FORMAT-REFERENCE.md](docs/FORMAT-REFERENCE.md) — struttura di ogni formato
- [docs/REUSABILITY.md](docs/REUSABILITY.md) — template DOCX, nuovi formati, pipeline
