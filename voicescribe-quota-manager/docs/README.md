# Quota Manager Service

Servizio generico per la gestione delle quote in modelli freemium. Gestisce limiti giornalieri con Redis per operazioni in tempo reale e PostgreSQL per persistenza e analytics.

## Caratteristiche

- **Check quota** senza consumare
- **Consume** atomico (INCR + EXPIRE in pipeline Redis)
- **Rollback** idempotente in caso di fallimento downstream
- Scrittura asincrona su PostgreSQL (non blocca mai la risposta)
- API REST documentate con OpenAPI
- Health check e metriche Prometheus

## Avvio standalone

### Con Docker Compose

```bash
docker compose up -d
```

Il servizio è disponibile su `http://localhost:8002`.

### Variabili d'ambiente

Copia `.env.example` in `.env` e configura:

- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- `DATABASE_URL` (formato `postgresql+asyncpg://...`)
- `INTERNAL_SERVICE_TOKEN` (obbligatorio per autenticazione inter-servizio)
- `FREE_TIER_DAILY_LIMIT` (default: 2)

## Test

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Per i test di integrazione Redis (testcontainers):

```bash
pytest tests/test_integration_redis.py -v
```

## Integrazione in un altro progetto

1. Includi questo servizio come dipendenza o avvialo come container
2. Configura `INTERNAL_SERVICE_TOKEN` identico in tutti i servizi
3. Chiama `GET /quota/check/{tenant_id}` prima di procedere
4. Se `allowed: true`, chiama `POST /quota/consume/{tenant_id}`
5. In caso di errore downstream, chiama `POST /quota/rollback/{tenant_id}`

Ogni richiesta deve includere l'header `X-Internal-Token`.

## Endpoint

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | /quota/check/{tenant_id} | Verifica quota senza consumare |
| POST | /quota/consume/{tenant_id} | Consuma 1 unità (429 se superato) |
| GET | /quota/status/{tenant_id} | Stato quota attuale |
| POST | /quota/rollback/{tenant_id} | Ripristina 1 unità |
| GET | /analytics | Analytics per candidati upgrade |
| GET | /health | Health check |
| GET | /metrics | Metriche Prometheus |

## Documentazione API

- Swagger UI: `http://localhost:8002/docs`
- OpenAPI JSON: `http://localhost:8002/openapi.json`
