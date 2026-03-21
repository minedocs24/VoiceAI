#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${DB_BACKUP_DIR:-./backups}"
RETENTION_DAYS="${DB_BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="voicescribe_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${VOICESCRIBE_DB_NAME:-voicescribe}" \
  -Fc > "${BACKUP_DIR}/${FILENAME}"

find "$BACKUP_DIR" -type f -name "voicescribe_*.dump" -mtime +"$RETENTION_DAYS" -delete

echo "[db-backup] Backup creato: ${BACKUP_DIR}/${FILENAME}"
echo "[db-backup] Retention applicata: ${RETENTION_DAYS} giorni"
