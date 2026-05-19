#!/usr/bin/env bash
# Boots a full demo environment with realistic data in ~60 seconds.
# Use before every demo call.
#
# Usage:  ./tools/seed_demo.sh
# Env:    DAYS=30 API_PORT=8000

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools"
BACKEND="$ROOT/backend"
COMPOSE="docker compose -f $BACKEND/docker-compose.yml"

API_PORT="${API_PORT:-8000}"
DAYS="${DAYS:-30}"
DEMO_EMAIL="demo@agentcogs.dev"
DB_URL="postgresql://postgres:dev@localhost:5433/agentcogs"
REDIS_URL="redis://localhost:6379"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${YELLOW}→${NC} $1"; }

command -v docker >/dev/null || { echo "docker required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 required"; exit 1; }

info "Step 1: Boot Postgres + Redis"
cd "$BACKEND"
$COMPOSE up -d postgres redis
cd "$ROOT"

info "Waiting for Postgres..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
  [[ $i -eq 30 ]] && { echo "Postgres timeout"; exit 1; }
done
pass "Postgres + Redis up"

info "Step 2: Schema + demo workspace"
$COMPOSE exec -T postgres psql -U postgres -d agentcogs \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true
$COMPOSE exec -T postgres psql -U postgres -d agentcogs \
  < "$BACKEND/migrations/versions/001_init.sql" >/dev/null

DEMO_KEY="acg_live_DEMO_$(openssl rand -hex 8)"
$COMPOSE exec -T postgres psql -U postgres -d agentcogs -v ON_ERROR_STOP=1 >/dev/null <<EOSQL
INSERT INTO workspaces (name, email, api_key, plan)
VALUES ('Patternstack', '$DEMO_EMAIL', '$DEMO_KEY', 'pro')
ON CONFLICT (email) DO UPDATE SET
  name = EXCLUDED.name,
  api_key = EXCLUDED.api_key,
  plan = 'pro';
EOSQL

WS_ID=$($COMPOSE exec -T postgres psql -U postgres -d agentcogs -tAc \
  "SELECT id::text FROM workspaces WHERE email='$DEMO_EMAIL';")
WS_ID=$(echo "$WS_ID" | tr -d '[:space:]')
if ! [[ "$WS_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
  echo "Invalid workspace id: $WS_ID"
  exit 1
fi
pass "Workspace id=$WS_ID"

cat > "$TOOLS/.demo_env" <<EOF
DEMO_WORKSPACE_ID=$WS_ID
DEMO_API_KEY=$DEMO_KEY
DEMO_EMAIL=$DEMO_EMAIL
EOF

info "Step 3: Start backend on :$API_PORT"
pip install -q httpx 2>/dev/null || true
# shellcheck disable=SC1091
source "$TOOLS/demo_daemon.sh"
export API_PORT DATABASE_URL="$DB_URL" REDIS_URL
demo_start_backend || { echo "Backend failed to start"; exit 1; }
pass "Backend healthy (daemon — survives terminal close)"

info "Step 4: Generate + post $DAYS days of synthetic events (40 personas)"
python3 "$TOOLS/generate_events.py" \
  --mode post \
  --days "$DAYS" \
  --endpoint "http://localhost:$API_PORT" \
  --api-key "$DEMO_KEY" \
  --workspace-id "$WS_ID" \
  --rate 600 \
  --seed 42
pass "Events ingested"

info "Step 5: Sync customers from personas.py (revenue, budget, names)"
python3 "$TOOLS/seed_customers.py" --workspace-id "$WS_ID" | \
  $COMPOSE exec -T postgres psql -U postgres -d agentcogs -v ON_ERROR_STOP=1 >/dev/null
pass "Customers synced from personas"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Demo environment ready — Patternstack"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Dashboard:     ./tools/start_demo.sh  →  http://localhost:5173/demo"
echo "               (or: cd dashboard && npm run dev)"
echo "API:           http://localhost:$API_PORT"
echo "Workspace ID:  $WS_ID"
echo "API Key:       $DEMO_KEY"
echo ""
echo "Login:         open http://localhost:5173/demo  (auto session)"
echo "               or dev-login with $DEMO_EMAIL"
echo ""
echo "Verify:        ./tools/verify_demo.sh"
echo "Stop stack:    ./tools/stop_demo.sh"
echo ""
echo "Live drift (separate terminal):"
echo "  source tools/.demo_env"
echo "  python3 tools/live_drift.py \\"
echo "    --workspace-id \"\$DEMO_WORKSPACE_ID\" \\"
echo "    --api-key \"\$DEMO_API_KEY\" \\"
echo "    --interactive"
echo ""
echo "Week-0 terminal demo:  python3 prototype/demo.py"
echo ""
