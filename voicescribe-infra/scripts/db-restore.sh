#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 /path/to/backup.dump" >&2
  exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file non trovato: $BACKUP_FILE" >&2
  exit 1
fi

DB_NAME="${VOICESCRIBE_DB_NAME:-voicescribe}"
DB_USER="${POSTGRES_USER:-postgres}"

ROW_COUNT="$(docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")"

if [ "${ROW_COUNT}" -gt 0 ]; then
  read -r -p "Il database contiene gia tabelle. Continuare con restore? [yes/NO] " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "Restore annullato"
    exit 1
  fi
fi

docker compose exec -T postgres pg_restore \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --clean --if-exists --no-owner --no-privileges < "$BACKUP_FILE"

echo "[db-restore] Ripristino completato da ${BACKUP_FILE}"
