#!/usr/bin/env bash
set -euo pipefail

SERVICES=(
  "SVC-01|http://localhost:8000/health"
  "SVC-02|http://localhost:8001/health"
  "SVC-03|http://localhost:8002/health"
  "SVC-04|http://localhost:8003/health"
  "SVC-05|http://localhost:8004/health"
  "SVC-06|http://localhost:8005/health"
  "SVC-07|http://localhost:8006/health"
  "SVC-08|http://localhost:8007/health"
  "NGINX|http://localhost:8080/health"
)

printf "%-10s %-8s %s\n" "SERVICE" "STATUS" "URL"
printf "%-10s %-8s %s\n" "-------" "------" "---"

FAIL=0
for item in "${SERVICES[@]}"; do
  NAME="${item%%|*}"
  URL="${item##*|}"

  if curl -fsS --max-time 3 "$URL" >/dev/null 2>&1; then
    printf "%-10s %-8s %s\n" "$NAME" "OK" "$URL"
  else
    printf "%-10s %-8s %s\n" "$NAME" "DOWN" "$URL"
    FAIL=1
  fi
done

if [ "$FAIL" -ne 0 ]; then
  echo "[healthcheck] Almeno un servizio non risponde"
  exit 1
fi

echo "[healthcheck] Tutti i servizi configurati rispondono"
