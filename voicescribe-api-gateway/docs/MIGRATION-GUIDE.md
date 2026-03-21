# Guida migrazione API

## Versioning

L'API usa versioning nell'URL: `/v1/...`. Un MAJOR bump (es. v1 → v2) introduce breaking changes.

## Preparazione al MAJOR bump

1. **Deprecation period**: gli endpoint deprecati restano disponibili per almeno 6 mesi con header `Deprecation: true` e `Sunset: <data>`
2. **Changelog**: documentare tutte le modifiche in CHANGELOG.md
3. **Comunicazione**: avvisare i client con almeno 3 mesi di anticipo

## Modifiche comuni

### Nuovi campi in risposta

- Aggiungere campi opzionali non rompe la compatibilità
- I client esistenti ignorano i campi sconosciuti

### Rimozione campi

- Breaking change
- Introdurre deprecation, poi rimuovere nel MAJOR successivo

### Nuovi endpoint

- Non breaking
- Documentare in OpenAPI

### Modifica formato richiesta

- Breaking
- Creare nuovo endpoint o versione

## Esempio migrazione v1 → v2

1. Mantenere `/v1/` attivo
2. Introdurre `/v2/` con le nuove API
3. Header `X-API-Version: 2` opzionale per richiedere v2
4. Dopo periodo di transizione, deprecare v1
