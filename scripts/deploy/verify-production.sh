#!/usr/bin/env bash
set -euo pipefail

API="${AGENTCOGS_API_URL:-https://api.agentcogs.dev}"
APP="${AGENTCOGS_APP_URL:-https://app.agentcogs.dev}"

echo "API  $API"
curl -fsS "$API/health" | head -c 200
echo ""
curl -fsS "$API/health/ready" | head -c 400
echo ""
echo "APP  $APP"
code=$(curl -sS -o /dev/null -w "%{http_code}" "$APP")
echo "HTTP $code"
test "$code" = "200" -o "$code" = "307" -o "$code" = "308"
