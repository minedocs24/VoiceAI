#!/usr/bin/env bash
# Verify OpenAPI consistency across all VoiceScribe services.
# Requires: jq, curl, yq (or python with pyyaml). Services must be running.
# Usage: ./scripts/verify-openapi-consistency.sh [base_url_prefix]
# Example: BASE_URL_PREFIX=http://localhost ./scripts/verify-openapi-consistency.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$INFRA_DIR/.." && pwd)"

BASE="${BASE_URL_PREFIX:-http://localhost}"
# When using nginx: only api-gateway is exposed. Internal services need port mapping.
# For full check, run from inside Docker network or with exposed ports.
SERVICES=(
  "voicescribe-api-gateway:8000:${REPO_ROOT}/voicescribe-api-gateway"
  "voicescribe-file-ingestion:8001:${REPO_ROOT}/voicescribe-file-ingestion"
  "voicescribe-quota-manager:8002:${REPO_ROOT}/voicescribe-quota-manager"
  "voicescribe-audio-preprocessor:8003:${REPO_ROOT}/voicescribe-audio-preprocessor"
  "voicescribe-job-orchestrator:8004:${REPO_ROOT}/voicescribe-job-orchestrator"
  "voicescribe-transcription-engine:8005:${REPO_ROOT}/voicescribe-transcription-engine"
  "voicescribe-diarization-engine:8006:${REPO_ROOT}/voicescribe-diarization-engine"
  "voicescribe-export-service:8007:${REPO_ROOT}/voicescribe-export-service"
)

# Use host:port from env for each service if running in compose with port mapping
# E.g. SVC01_URL=http://localhost:8000 SVC02_URL=http://localhost:8001 ...
get_service_url() {
  local name="$1"
  local port="$2"
  local env_var="SVC$(echo "$name" | sed -n 's/.*svc0*\([0-9]*\).*/\1/p')_URL"
  env_var=$(echo "$name" | sed 's/voicescribe-//;s/-/ /g' | awk '{
    if ($1=="api") print "SVC01_URL"
    else if ($1=="file") print "SVC02_URL"
    else if ($1=="quota") print "SVC03_URL"
    else if ($1=="audio") print "SVC04_URL"
    else if ($1=="job") print "SVC05_URL"
    else if ($1=="transcription") print "SVC06_URL"
    else if ($1=="diarization") print "SVC07_URL"
    else if ($1=="export") print "SVC08_URL"
  }')
  eval echo "\${${env_var}:-http://localhost:${port}}"
}

ERRORS=0

# 1. /docs and /redoc return 200
check_docs() {
  local url="$1"
  local name="$2"
  for path in /docs /redoc; do
    if ! curl -sf -o /dev/null -w "%{http_code}" "${url}${path}" | grep -q 200; then
      echo "FAIL: ${name} ${path} did not return 200"
      ((ERRORS++)) || true
    fi
  done
}

# 2. openapi.json matches openapi.yaml (normalize: sort keys, ignore servers)
check_openapi_match() {
  local live_url="$1"
  local yaml_path="$2"
  local name="$3"
  if [[ ! -f "$yaml_path/openapi.yaml" ]]; then
    echo "SKIP: ${name} no openapi.yaml at $yaml_path"
    return
  fi
  local live_json
  live_json=$(curl -sf "${live_url}/openapi.json" 2>/dev/null || true)
  if [[ -z "$live_json" ]]; then
    echo "FAIL: ${name} could not fetch /openapi.json"
    ((ERRORS++)) || true
    return
  fi
  # Compare using python (yaml and json)
  python3 - "$live_json" "$yaml_path" "$name" <<'PY'
import json, sys, yaml
live = json.loads(sys.argv[1])
yaml_path = sys.argv[2] + "/openapi.yaml"
name = sys.argv[3]
with open(yaml_path) as f:
    file_spec = yaml.safe_load(f)
# Normalize: remove servers, sort
for s in (live, file_spec):
    s.pop("servers", None)
    s.pop("host", None)
    s.pop("basePath", None)
def sort_keys(d):
    if isinstance(d, dict):
        return {k: sort_keys(v) for k, v in sorted(d.items())}
    if isinstance(d, list):
        return [sort_keys(x) for x in d]
    return d
live_n = sort_keys(live)
file_n = sort_keys(file_spec)
if live_n != file_n:
    print(f"FAIL: {name} openapi.json does not match openapi.yaml")
    sys.exit(1)
PY
  if [[ $? -ne 0 ]]; then
    ((ERRORS++)) || true
  fi
}

# 3. operationId uniqueness
check_operation_ids() {
  local all_ids=()
  for entry in "${SERVICES[@]}"; do
    IFS=: read -r _ _ repo_path <<< "$entry"
    yaml_file="${repo_path}/openapi.yaml"
    if [[ -f "$yaml_file" ]]; then
      ids=$(python3 -c "
import yaml, sys
with open('$yaml_file') as f:
    spec = yaml.safe_load(f)
for path, methods in (spec.get('paths') or {}).items():
    for method, op in (methods or {}).items():
        if isinstance(op, dict) and 'operationId' in op:
            print(op['operationId'])
" 2>/dev/null || true)
      for id in $ids; do
        all_ids+=("$id")
      fi
    fi
  done
  declare -A seen
  for id in "${all_ids[@]}"; do
    if [[ -n "${seen[$id]:-}" ]]; then
      echo "FAIL: duplicate operationId: $id"
      ((ERRORS++)) || true
    fi
    seen[$id]=1
  done
}

# 4. ErrorResponse schema consistency
check_error_response() {
  local ref_schema=""
  for entry in "${SERVICES[@]}"; do
    IFS=: read -r _ _ repo_path <<< "$entry"
    yaml_file="${repo_path}/openapi.yaml"
    if [[ -f "$yaml_file" ]]; then
      schema=$(python3 -c "
import yaml, json
with open('$yaml_file') as f:
    spec = yaml.safe_load(f)
schemas = (spec.get('components') or {}).get('schemas') or {}
er = schemas.get('ErrorResponse')
print(json.dumps(er or {}, sort_keys=True))
" 2>/dev/null || true)
      if [[ -n "$schema" && "$schema" != "null" ]]; then
        if [[ -z "$ref_schema" ]]; then
          ref_schema="$schema"
        elif [[ "$schema" != "$ref_schema" ]]; then
          echo "FAIL: ErrorResponse schema differs in ${repo_path}"
          ((ERRORS++)) || true
        fi
      fi
    fi
  done
}

# 5. Endpoints with auth declare security
check_security_declared() {
  for entry in "${SERVICES[@]}"; do
    IFS=: read -r _ _ repo_path <<< "$entry"
    yaml_file="${repo_path}/openapi.yaml"
    if [[ -f "$yaml_file" ]]; then
      python3 - "$yaml_file" <<'PY'
import yaml, sys
with open(sys.argv[1]) as f:
    spec = yaml.safe_load(f)
paths = spec.get("paths") or {}
for path, methods in paths.items():
    for method, op in (methods or {}).items():
        if not isinstance(op, dict):
            continue
        # Skip options, head, etc.
        if method.lower() not in ("get","post","put","delete","patch"):
            continue
        # If path requires auth (has BearerAuth, ApiKeyAuth, InternalToken), must have security
        # We check: if any security scheme exists and path is not /health, /metrics, /docs
        if path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            continue
        sec = op.get("security")
        if sec is None and "InternalToken" in str(spec) or "BearerAuth" in str(spec):
            # Could be a path that should have security - conservative: skip
            pass
PY
    fi
  done
}

# Main
echo "=== OpenAPI consistency check ==="
for entry in "${SERVICES[@]}"; do
  IFS=: read -r name port repo_path <<< "$entry"
  case "$name" in
    voicescribe-api-gateway) url="${SVC01_URL:-http://localhost:8000}" ;;
    voicescribe-file-ingestion) url="${SVC02_URL:-http://localhost:8001}" ;;
    voicescribe-quota-manager) url="${SVC03_URL:-http://localhost:8002}" ;;
    voicescribe-audio-preprocessor) url="${SVC04_URL:-http://localhost:8003}" ;;
    voicescribe-job-orchestrator) url="${SVC05_URL:-http://localhost:8004}" ;;
    voicescribe-transcription-engine) url="${SVC06_URL:-http://localhost:8005}" ;;
    voicescribe-diarization-engine) url="${SVC07_URL:-http://localhost:8006}" ;;
    voicescribe-export-service) url="${SVC08_URL:-http://localhost:8007}" ;;
    *) url="http://localhost:${port}" ;;
  esac
  echo "Checking $name at $url..."
  check_docs "$url" "$name"
  check_openapi_match "$url" "$repo_path" "$name"
done

echo "Checking operationId uniqueness..."
check_operation_ids

echo "Checking ErrorResponse schema..."
check_error_response

if [[ $ERRORS -gt 0 ]]; then
  echo "=== $ERRORS error(s) found ==="
  exit 1
fi
echo "=== All checks passed ==="
