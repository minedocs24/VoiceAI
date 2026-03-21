# Guida al riuso del Quota Manager

Questo servizio è progettato per essere riutilizzato in qualsiasi prodotto con modello freemium, indipendentemente dal dominio (trascrizione, storage, API calls, ecc.).

## Variabili d'ambiente da modificare

| Variabile | Descrizione | Esempio per altro prodotto |
|-----------|-------------|----------------------------|
| `FREE_TIER_DAILY_LIMIT` | Limite giornaliero default | `10` per 10 operazioni/giorno |
| `REDIS_DB` | Database Redis dedicato | `3` per evitare conflitti |
| `INTERNAL_SERVICE_TOKEN` | Token condiviso con i tuoi servizi | Genera un token sicuro |

## Configurazione `config/quota.yml`

- `quota.daily_limit`: limite giornaliero (override da env)
- `quota.upgrade_candidate_threshold`: soglia `quota_exceeded_attempts` per considerare un tenant candidato all'upgrade
- `quota.retention_days`: giorni di storico da conservare

## Integrazione analytics con CRM / Marketing

L'endpoint `GET /analytics` restituisce i tenant ordinati per `quota_exceeded_attempts` (decrescente). Filtri:

- `from_date`, `to_date`: intervallo date
- `min_exceeded`: soglia minima tentativi bloccati
- `page`, `page_size`: paginazione

I dati possono essere usati per:

1. **Webhook** verso CRM (HubSpot, Salesforce) per creare lead/opportunità
2. **Export periodico** verso sistemi di marketing automation
3. **Dashboard** interne per vendite

## Schema database

La tabella `free_tier_usage` ha:

- `tenant_id`: identificativo tenant
- `usage_date`: data (UTC)
- `used_count`: operazioni consumate
- `quota_exceeded_attempts`: tentativi oltre quota (bloccati)

È necessario che la tabella `tenants` esista con almeno `id` e `is_active`.

## Estrazione in un progetto separato

1. Copia la directory `app/`, `config/`, `openapi.yaml`, `migrations/`
2. Adatta `config/quota.yml` ai tuoi limiti
3. Esegui le migrazioni sul tuo database
4. Configura Redis e PostgreSQL
5. Avvia con `uvicorn app.main:app --host 0.0.0.0 --port 8002`
