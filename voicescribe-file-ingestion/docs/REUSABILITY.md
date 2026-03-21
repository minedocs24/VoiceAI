# Reusability Guide - File Ingestion Service

Questo servizio e' pensato per essere riutilizzato in qualsiasi prodotto che richieda upload file robusto e validato.

## Leve di riuso principali

1. **Whitelist formati** (`config/ingestion.yml`)
   - Definisci estensione + magic bytes per il tuo dominio.
   - Esempio imaging: png, jpg, tif.
   - Esempio office: pdf, docx, xlsx.

2. **Storage pattern**
   - Configura `storage.path_pattern` per adattarlo alla tua gerarchia.
   - Pattern default: `{base}/{tenant_id}/{job_id}/{uuid}.{ext}`.

3. **Limiti operativi**
   - `UPLOAD_MAX_BYTES`
   - `probe_timeout_seconds`
   - `temp_file_max_age_seconds`

4. **Verifiche opzionali**
   - `X-Expected-SHA256` per integrita' end-to-end.
   - `X-Free-Tier` per regole di business su durata.

## Esempio configurazione non-audio

```yaml
formats:
  pdf:
    magic_bytes:
      - "25 50 44 46"
  png:
    magic_bytes:
      - "89 50 4E 47 0D 0A 1A 0A"
```

## Integrazione consigliata

- Esporre il servizio solo su rete interna.
- Demandare auth utente al gateway e usare token inter-servizio interno.
- Collezionare metriche Prometheus per validazione/reject trend.