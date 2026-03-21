#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRT_PATH="${CERT_DIR}/voicescribe.crt"
KEY_PATH="${CERT_DIR}/voicescribe.key"

DAYS="${1:-365}"
CN="${2:-localhost}"

echo "[certs] Generazione certificato self-signed CN=${CN}, validita ${DAYS} giorni"
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout "${KEY_PATH}" \
  -out "${CRT_PATH}" \
  -days "${DAYS}" \
  -subj "/C=IT/ST=RM/L=Rome/O=VoiceScribe/CN=${CN}" \
  -addext "subjectAltName=DNS:${CN},DNS:localhost,IP:127.0.0.1"

chmod 600 "${KEY_PATH}"
chmod 644 "${CRT_PATH}"

echo "[certs] Certificato generato: ${CRT_PATH}"
echo "[certs] Chiave privata generata: ${KEY_PATH}"
