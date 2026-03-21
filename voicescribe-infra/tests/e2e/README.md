# E2E Tests VoiceScribe

Test end-to-end con stack Docker Compose completo.

## Prerequisiti

1. `docker compose up -d` da `voicescribe-infra`
2. Migrazioni: `alembic -c migrations/alembic.ini upgrade head`
3. Seed utenti: `docker compose exec -T postgres psql -U voicescribe_app -d voicescribe < scripts/seed-e2e-users.sql`
4. File audio di test in `fixtures/`:
   - `test_audio_2min.mp3` - 2 minuti (Scenario 1, 4)
   - `test_audio_2speakers.mp3` - 2 speaker (Scenario 2)
   - `test_audio_45min.mp3` - 45 min (Scenario 3, opzionale)

## Esecuzione

```bash
cd voicescribe-infra
E2E_BASE_URL=https://localhost E2E_VERIFY_SSL=false pytest tests/e2e/ -v -m e2e
```

Per dev (HTTP): `E2E_BASE_URL=http://localhost:8080`

## Scenari

1. **Free Tier**: login, upload, download TXT/SRT, 403 DOCX, quota 429
2. **PRO Diarization**: API key, SPEAKER_00/01, DOCX valido
3. **Resilience**: 422 su file 45 min, path traversal rejected
4. **Load**: upload paralleli, quote rispettate
