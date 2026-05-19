#!/usr/bin/env bash
# Verify README links: repo files exist; optional HTTP checks for production URLs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="$ROOT/README.md"
fail=0

check_file() {
  local rel="$1"
  local path="$ROOT/$rel"
  if [[ -f "$path" ]]; then
    echo "OK  file  $rel"
  else
    echo "FAIL file  $rel"
    fail=1
  fi
}

# Relative markdown links from README
while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  rel="${rel%%#*}"
  check_file "$rel"
done < <(grep -oE '\]\([^)]+\)' "$README" | sed 's/](//;s/)//' | grep -v '^https\?://' | grep -v '^#' || true)

# Production URLs (best-effort)
check_http() {
  local url="$1"
  local code
  code=$(curl -sS -m 15 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^(200|301|302|307|308)$ ]]; then
    echo "OK  http $code $url"
  else
    echo "WARN http $code $url"
  fi
}

check_http "https://agentcogs-api-production.up.railway.app/health"
check_http "https://github.com/vaibhav11123/agentcogs/actions/workflows/ci.yml"

exit "$fail"
