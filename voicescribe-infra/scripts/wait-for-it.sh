#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 host port [timeout_seconds]" >&2
  exit 1
fi

HOST="$1"
PORT="$2"
TIMEOUT="${3:-30}"
START_TS="$(date +%s)"

while true; do
  if (echo >"/dev/tcp/${HOST}/${PORT}") >/dev/null 2>&1; then
    echo "[wait-for-it] ${HOST}:${PORT} raggiungibile"
    exit 0
  fi

  NOW_TS="$(date +%s)"
  ELAPSED="$((NOW_TS - START_TS))"
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "[wait-for-it] Timeout dopo ${TIMEOUT}s su ${HOST}:${PORT}" >&2
    exit 1
  fi

  sleep 1
done
