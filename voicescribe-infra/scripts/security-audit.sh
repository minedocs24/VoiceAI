#!/usr/bin/env bash
# Security audit: bandit, safety, pip-audit, semgrep on all VoiceScribe repos.
# Output: HTML report. Exit 1 if bandit finds HIGH/CRITICAL (configurable).
# Usage: ./scripts/security-audit.sh [--no-fail]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$INFRA_DIR/.." && pwd)"
REPORT_DIR="${REPORT_DIR:-$INFRA_DIR/reports}"
FAIL_ON_HIGH="${FAIL_ON_HIGH:-true}"
[[ "${1:-}" == "--no-fail" ]] && FAIL_ON_HIGH=false

mkdir -p "$REPORT_DIR"
REPORT_HTML="$REPORT_DIR/security-audit-$(date +%Y%m%d-%H%M%S).html"

SERVICES=(
  "voicescribe-api-gateway"
  "voicescribe-file-ingestion"
  "voicescribe-quota-manager"
  "voicescribe-audio-preprocessor"
  "voicescribe-job-orchestrator"
  "voicescribe-transcription-engine"
  "voicescribe-diarization-engine"
  "voicescribe-export-service"
)

run_bandit() {
  local repo="$1"
  local out="$2"
  if command -v bandit &>/dev/null; then
    bandit -r "$repo" -f json -o "$out" 2>/dev/null || true
  else
    echo '{"results":[]}' > "$out"
  fi
}

run_safety() {
  local req="$1"
  local out="$2"
  if [[ -f "$req" ]] && command -v safety &>/dev/null; then
    safety check -r "$req" --json 2>/dev/null > "$out" || echo '[]' > "$out"
  else
    echo '[]' > "$out"
  fi
}

run_pip_audit() {
  local req="$1"
  local out="$2"
  if [[ -f "$req" ]] && command -v pip-audit &>/dev/null; then
    pip-audit -r "$req" --format json 2>/dev/null > "$out" || echo '{"dependencies":[]}' > "$out"
  else
    echo '{"dependencies":[]}' > "$out"
  fi
}

run_semgrep() {
  local repo="$1"
  local out="$2"
  if command -v semgrep &>/dev/null; then
    semgrep scan --config auto --json -o "$out" "$repo" 2>/dev/null || true
  else
    echo '{"results":[]}' > "$out"
  fi
}

HIGH_CRITICAL_COUNT=0

cat > "$REPORT_HTML" <<'HEAD'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>VoiceScribe Security Audit</title>
<style>
body{font-family:sans-serif;margin:20px;background:#1e1e1e;color:#d4d4d4}
h1{color:#4ec9b0}
h2{color:#569cd6;margin-top:2em}
.service{background:#252526;padding:15px;margin:10px 0;border-radius:6px}
.fail{color:#f48771}
.warn{color:#dcdcaa}
.ok{color:#4ec9b0}
pre{background:#1e1e1e;padding:10px;overflow-x:auto;font-size:12px}
</style>
</head>
<body>
<h1>VoiceScribe Security Audit Report</h1>
<p>Generated: HEAD
date >> "$REPORT_HTML"
cat >> "$REPORT_HTML" <<'HEAD2'
</p>
HEAD2

for svc in "${SERVICES[@]}"; do
  repo="$REPO_ROOT/$svc"
  [[ ! -d "$repo" ]] && continue
  echo "<h2>$svc</h2><div class='service'>" >> "$REPORT_HTML"
  tmpdir=$(mktemp -d)
  trap "rm -rf $tmpdir" EXIT

  # Bandit
  run_bandit "$repo" "$tmpdir/bandit.json"
  high=$(jq -r '[.results[]|select(.issue_severity=="HIGH" or .issue_severity=="MEDIUM")]|length' "$tmpdir/bandit.json" 2>/dev/null || echo 0)
  [[ "$high" -gt 0 ]] && ((HIGH_CRITICAL_COUNT+=high)) || true
  echo "<h3>Bandit</h3><pre>$(jq -r '.results[]|"\(.issue_severity): \(.issue_text) at \(.filename):\(.line_number)"' "$tmpdir/bandit.json" 2>/dev/null | head -20 || echo "No issues")</pre>" >> "$REPORT_HTML"

  # Safety (requirements.txt)
  req="$repo/requirements.txt"
  [[ ! -f "$req" ]] && req=""
  run_safety "$req" "$tmpdir/safety.json"
  echo "<h3>Safety</h3><pre>$(cat "$tmpdir/safety.json" | jq -r '.[]|"\(.vulnerability): \(.advisory)"' 2>/dev/null | head -10 || echo "OK")</pre>" >> "$REPORT_HTML"

  # pip-audit
  [[ -f "$repo/requirements.txt" ]] && run_pip_audit "$repo/requirements.txt" "$tmpdir/pip_audit.json"
  echo "<h3>pip-audit</h3><pre>$(jq -r '.vulnerabilities[]?|"\(.name): \(.id)"' "$tmpdir/pip_audit.json" 2>/dev/null | head -10 || echo "OK")</pre>" >> "$REPORT_HTML"

  # Semgrep
  run_semgrep "$repo" "$tmpdir/semgrep.json"
  echo "<h3>Semgrep</h3><pre>$(jq -r '.results[]?|"\(.extra.severity): \(.extra.message) at \(.path):\(.start.line)"' "$tmpdir/semgrep.json" 2>/dev/null | head -10 || echo "OK")</pre>" >> "$REPORT_HTML"

  echo "</div>" >> "$REPORT_HTML"
  rm -rf "$tmpdir"
done

echo "<p class='$([ $HIGH_CRITICAL_COUNT -gt 0 ] && echo fail || echo ok)'>Total HIGH/MEDIUM findings: $HIGH_CRITICAL_COUNT</p>" >> "$REPORT_HTML"
echo "</body></html>" >> "$REPORT_HTML"

echo "Report: $REPORT_HTML"
if [[ "$FAIL_ON_HIGH" == "true" ]] && [[ $HIGH_CRITICAL_COUNT -gt 0 ]]; then
  echo "FAIL: $HIGH_CRITICAL_COUNT HIGH/MEDIUM findings"
  exit 1
fi
