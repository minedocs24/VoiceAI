# VoiceScribe File Ingestion Service (SVC-02)

Servizio di ingestion per upload file binari in streaming con validazione estensione + magic bytes, probe metadata con FFmpeg e persistenza metadata su PostgreSQL.

## Feature principali

- Upload streaming chunk-by-chunk (no full buffering in RAM)
- Validazione a tre livelli:
  - estensione dichiarata
  - magic bytes reali
  - durata Free Tier (opzionale via header `X-Free-Tier`)
- Hash SHA-256 calcolato durante upload
- Storage sicuro con path pattern `{base}/{tenant_id}/{job_id}/{uuid}.{ext}`
- Endpoint probe con cache Redis
- Endpoint health e metrics Prometheus
- Cleanup periodico file temporanei

## Configurazione

1. Copia `.env.example` in `.env`
2. Modifica variabili chiave:
   - `STORAGE_BASE_PATH`
   - `UPLOAD_MAX_BYTES`
   - `DATABASE_URL`
   - `REDIS_*`
   - `INTERNAL_SERVICE_TOKEN`
3. Adatta `config/ingestion.yml` per whitelist formati e parametri probe

### Riuso in altri contesti

Il servizio non dipende dal dominio audio VoiceScribe: puoi cambiare whitelist e firme magic bytes in `config/ingestion.yml` per documenti, immagini o altri binari.

## Avvio locale

```bash
pip install -e .[dev]
python run.py
```

## Avvio Docker

```bash
docker build -t voicescribe-file-ingestion .
docker run --rm -p 8001:8001 -v /host/data/input:/data/input voicescribe-file-ingestion
```

## Endpoint

- `POST /upload`
- `GET /files/{job_id}`
- `DELETE /files/{job_id}`
- `GET /probe/{job_id}`
- `GET /health`
- `GET /metrics`

Contratto completo: `openapi.yaml`.