# VoiceScribe API Gateway (SVC-01)

Punto di ingresso pubblico unico per VoiceScribe AI. Gestisce autenticazione, rate limiting, orchestrazione tra servizi e documentazione aggregata.

## Autenticazione

### Free Tier (email + password)

1. **Login** per ottenere access token e refresh token:

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your-password"}'
```

Risposta:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

2. Usa l'access token nelle richieste:

```bash
curl -X POST http://localhost:8000/v1/transcribe \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@audio.mp3"
```

### PRO/Enterprise (API Key)

1. Ottieni una API key dal formato `vs_live_{32 caratteri}` (generata e salvata come SHA-256 nel DB).

2. Usa l'header `X-API-Key`:

```bash
curl -X POST http://localhost:8000/v1/transcribe \
  -H "X-API-Key: vs_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -F "file=@audio.mp3"
```

## Esempio completo: trascrizione end-to-end

```bash
# 1. Login (Free Tier)
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}' | jq -r '.access_token')

# 2. Upload file
RESP=$(curl -s -X POST http://localhost:8000/v1/transcribe \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3")
JOB_ID=$(echo $RESP | jq -r '.job_id')

# 3. Controlla stato
curl -s "http://localhost:8000/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"

# 4. Download (quando DONE)
curl -s "http://localhost:8000/v1/jobs/$JOB_ID/download/txt" \
  -H "Authorization: Bearer $TOKEN" -o transcript.txt
```

## Configurazione

1. Copia `.env.example` in `.env`
2. Configura variabili: `SVC02_URL`, `SVC03_URL`, `INTERNAL_SERVICE_TOKEN`, `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_*`
3. Esegui migration infra per schema `tenants` (email, password_hash)

## Avvio

```bash
pip install -e .
python run.py
```

Oppure con Docker:

```bash
docker build -t voicescribe-api-gateway .
docker run -p 8000:8000 --env-file .env voicescribe-api-gateway
```

## Endpoint

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | /v1/auth/login | Login Free Tier |
| POST | /v1/auth/refresh | Refresh token |
| POST | /v1/auth/logout | Logout |
| POST | /v1/transcribe | Upload per trascrizione |
| GET | /v1/jobs | Lista job |
| GET | /v1/jobs/{id} | Dettaglio job |
| GET | /v1/jobs/{id}/download/{fmt} | Download risultato |
| GET | /ws/jobs/{id} | WebSocket stato job |
| GET | /health | Health check |
| GET | /metrics | Prometheus |
| GET | /docs | Swagger UI |
| GET | /api-docs | Landpage documentazione |

## Documentazione

- [docs/AUTH.md](docs/AUTH.md) - Meccanismi autenticazione
- [docs/TIER-ENFORCEMENT.md](docs/TIER-ENFORCEMENT.md) - Policy per tier
- [docs/MIGRATION-GUIDE.md](docs/MIGRATION-GUIDE.md) - Guida migrazione API
