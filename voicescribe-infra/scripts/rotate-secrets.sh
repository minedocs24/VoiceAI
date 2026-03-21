#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
[rotate-secrets] Procedura consigliata rotazione segreti senza downtime

1) Preparazione
   - Generare nuovi segreti: DB password, REDIS_PASSWORD, INTERNAL_SERVICE_TOKEN, JWT keypair.
   - Salvare i nuovi valori nel vault aziendale.

2) Rotazione PostgreSQL (rolling)
   - Creare password secondaria utente applicativo.
   - Aggiornare servizi consumer con nuova password (deploy rolling).
   - Verificare connessioni attive con pg_stat_activity.
   - Revocare password precedente.

3) Rotazione Redis
   - Abilitare nuova password in finestra controllata.
   - Aggiornare tutti i client Celery/Redis.
   - Riavviare i worker in rolling per evitare perdita job in coda.

4) Rotazione token inter-service
   - Supportare doppio token temporaneo (current + next).
   - Deploy progressivo di tutti i servizi.
   - Rimuovere token legacy al termine.

5) Rotazione JWT/API Keys
   - Usare key versioning (kid) per periodo transitorio.
   - Mantenere valida la chiave precedente per la durata massima token.

6) Verifica finale
   - Eseguire scripts/healthcheck.sh
   - Controllare dashboard errori 5xx e autenticazione.
   - Registrare audit trail in OPERATIONS.md.
EOF
