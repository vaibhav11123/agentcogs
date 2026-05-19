#!/usr/bin/env bash
# Start local dev stack: Docker (Postgres+Redis), API, Dashboard.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Docker (Postgres :5433, Redis :6379)..."
cd "$ROOT/backend"
docker compose up -d

echo "Starting API on :8000..."
cd "$ROOT/backend"
source "$ROOT/.venv/bin/activate"
export $(grep -v '^#' .env | xargs)
PYTHONPATH=. uvicorn app.main:app --reload --port 8000 &
API_PID=$!

echo "Starting dashboard on :5173..."
cd "$ROOT/dashboard"
npm run dev &
WEB_PID=$!

echo ""
echo "✅ Dev stack running"
echo "   API:       http://localhost:8000/health"
echo "   Dashboard: http://localhost:5173"
echo "   Login:     test@example.com (dev-login)"
echo "   API key:   acg_live_TESTKEY"
echo ""
echo "Press Ctrl+C to stop API and dashboard (Docker keeps running)."
trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
wait
