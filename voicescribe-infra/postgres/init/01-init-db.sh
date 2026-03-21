#!/usr/bin/env bash
set -euo pipefail

: "${VOICESCRIBE_DB_NAME:?VOICESCRIBE_DB_NAME non impostata}"
: "${VOICESCRIBE_DB_USER:?VOICESCRIBE_DB_USER non impostata}"
: "${VOICESCRIBE_DB_PASSWORD:?VOICESCRIBE_DB_PASSWORD non impostata}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
DO
\$do\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${VOICESCRIBE_DB_USER}') THEN
        EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', '${VOICESCRIBE_DB_USER}', '${VOICESCRIBE_DB_PASSWORD}');
    END IF;
END
\$do\$;

SELECT format('CREATE DATABASE %I OWNER %I', '${VOICESCRIBE_DB_NAME}', '${VOICESCRIBE_DB_USER}')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${VOICESCRIBE_DB_NAME}')
\gexec

GRANT CONNECT ON DATABASE ${VOICESCRIBE_DB_NAME} TO ${VOICESCRIBE_DB_USER};
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$VOICESCRIBE_DB_NAME" <<-SQL
GRANT USAGE, CREATE ON SCHEMA public TO ${VOICESCRIBE_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${VOICESCRIBE_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO ${VOICESCRIBE_DB_USER};
SQL

# Esegue lo schema iniziale nel DB applicativo voicescribe
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$VOICESCRIBE_DB_NAME" -f /docker-entrypoint-initdb.d/02-initial-schema.sql.template

echo "[init-db] Database, permessi e schema VoiceScribe inizializzati correttamente."
