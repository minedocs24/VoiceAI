#!/usr/bin/env bash
set -euo pipefail

RAMDISK_PATH="${RAMDISK_PATH:-/mnt/ramdisk}"
RAMDISK_SIZE="${RAMDISK_SIZE:-32G}"
MIN_GB_REQUIRED=40

if ! command -v free >/dev/null 2>&1; then
  echo "Comando 'free' non disponibile" >&2
  exit 1
fi

TOTAL_GB="$(free -g | awk '/^Mem:/ {print $2}')"
if [ "$TOTAL_GB" -lt "$MIN_GB_REQUIRED" ]; then
  echo "RAM insufficiente: ${TOTAL_GB}GB trovati, richiesti almeno ${MIN_GB_REQUIRED}GB" >&2
  exit 1
fi

sudo mkdir -p "$RAMDISK_PATH"
sudo chmod 1777 "$RAMDISK_PATH"

FSTAB_LINE="tmpfs ${RAMDISK_PATH} tmpfs defaults,size=${RAMDISK_SIZE},mode=1777 0 0"
if ! grep -qE "^[^#]*[[:space:]]${RAMDISK_PATH}[[:space:]]tmpfs" /etc/fstab; then
  echo "$FSTAB_LINE" | sudo tee -a /etc/fstab >/dev/null
fi

if ! mountpoint -q "$RAMDISK_PATH"; then
  sudo mount "$RAMDISK_PATH"
fi

if mountpoint -q "$RAMDISK_PATH"; then
  echo "[ramdisk] Montaggio completato su ${RAMDISK_PATH} con size ${RAMDISK_SIZE}"
  df -h "$RAMDISK_PATH"
else
  echo "[ramdisk] Errore montaggio ${RAMDISK_PATH}" >&2
  exit 1
fi
