#!/usr/bin/env sh
set -eu

if [ -z "${REDIS_PASSWORD:-}" ]; then
  echo "REDIS_PASSWORD non impostata" >&2
  exit 1
fi

TMP_CONF="/tmp/redis-runtime.conf"
cp /usr/local/etc/redis/redis.conf "$TMP_CONF"
echo "requirepass ${REDIS_PASSWORD}" >> "$TMP_CONF"

exec redis-server "$TMP_CONF"
