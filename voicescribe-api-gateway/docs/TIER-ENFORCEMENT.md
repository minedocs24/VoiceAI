# Tier Enforcement

## Policy per tier

| Tier | Durata max | Quota giornaliera | Export | Diarization |
|------|------------|-------------------|--------|-------------|
| FREE | 30 min | 2 | txt, srt, json | No |
| PRO | 4 ore | Illimitata | + docx, vtt | Sì |
| ENTERPRISE | 24 ore | Personalizzata | + docx, vtt | Sì |

## Applicazione

- **Free Tier**: middleware controlla durata (SVC-02 con X-Free-Tier) e quota (SVC-03 check/consume) prima di accettare upload
- **PRO/Enterprise**: nessun controllo quota; upload diretto a SVC-02
- **Download**: formato verificato contro tier; Free non può scaricare DOCX (403)

## Cambio piano

- Il tier è letto da `tenants.tier` a ogni richiesta
- Upgrade: aggiornare `tenants.tier` → effetto immediato
- Downgrade: job in coda mantengono `tier_at_creation` per priorità Celery; nuovi job usano tier corrente

## Job in coda al momento dell'upgrade

- I job già in coda mantengono la priorità assegnata al momento della creazione
- Il consumo quota Free Tier è già stato effettuato; non viene restituito in caso di upgrade
