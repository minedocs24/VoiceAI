#!/usr/bin/env bash
set -euo pipefail

RAMDISK_PATH="${RAMDISK_PATH:-/mnt/ramdisk}"
MAX_AGE_HOURS="${1:-6}"

if [ ! -d "$RAMDISK_PATH" ]; then
  echo "Percorso ramdisk non trovato: $RAMDISK_PATH" >&2
  exit 1
fi

BEFORE_KB="$(du -sk "$RAMDISK_PATH" | awk '{print $1}')"
DELETED_FILES="$(find "$RAMDISK_PATH" -type f -mmin +$((MAX_AGE_HOURS * 60)) | wc -l)"

find "$RAMDISK_PATH" -type f -mmin +$((MAX_AGE_HOURS * 60)) -delete

AFTER_KB="$(du -sk "$RAMDISK_PATH" | awk '{print $1}')"
FREED_KB="$((BEFORE_KB - AFTER_KB))"

printf "[cleanup-ramdisk] File rimossi: %s\n" "$DELETED_FILES"
printf "[cleanup-ramdisk] Spazio recuperato: %s MB\n" "$((FREED_KB / 1024))"
printf "[cleanup-ramdisk] Parametro retention: %s ore\n" "$MAX_AGE_HOURS"
