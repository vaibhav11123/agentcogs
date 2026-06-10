#!/usr/bin/env bash
# Headless self-host smoke: compose up → dev-login → ingest → leaderboard row.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

cleanup() {
  docker compose down -v 2>/dev/null || true
}
trap cleanup EXIT

if [[ ! -f .env ]]; then
  cp .env.selfhost.example .env
fi

docker compose up -d --build

API="http://localhost:8000"
deadline=$((SECONDS + 120))
until curl -sf "$API/health/ready" >/dev/null 2>&1; do
  if (( SECONDS > deadline )); then
    echo "FAIL: /health/ready not ready within 120s"
    exit 1
  fi
  sleep 2
done

COOKIE_JAR="$(mktemp)"
DEV_JSON=$(curl -sf -c "$COOKIE_JAR" -X POST "$API/v1/auth/dev-login" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@selfhost.local","name":"Smoke Workspace"}')
API_KEY=$(echo "$DEV_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")

ME=$(curl -sf -b "$COOKIE_JAR" "$API/v1/auth/me")
echo "$ME" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'acg_live_' not in json.dumps(d)"

RUN_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
TS=$(date +%s)
curl -sf -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"run_id\":\"$RUN_ID\",\"customer_id\":\"smoke_cust\",\"workflow_id\":\"smoke\",\"ts\":$TS,\"status\":\"completed\",\"total_usd\":0.01,\"models\":{}}" >/dev/null

deadline=$((SECONDS + 60))
found=0
while (( SECONDS < deadline )); do
  if curl -sf -b "$COOKIE_JAR" "$API/v1/leaderboard" | grep -q smoke_cust; then
    found=1
    break
  fi
  sleep 2
done

rm -f "$COOKIE_JAR"

if [[ "$found" -eq 1 ]]; then
  echo "PASS: self-host smoke"
  exit 0
fi

echo "FAIL: smoke customer not on leaderboard"
exit 1
