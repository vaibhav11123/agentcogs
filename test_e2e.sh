#!/usr/bin/env bash
# AgentCOGS end-to-end test runner.
# Validates: SDK install, unit tests, backend boot, full ingest cycle,
# idempotency, budget enforcement, Redis counters.
#
# Usage:   ./test_e2e.sh
# Cleanup: ./test_e2e.sh --teardown
#
# Monorepo layout (default):
#   SDK_DIR=.          (repo root)
#   BACKEND_DIR=./backend

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SDK_DIR="${SDK_DIR:-$ROOT}"
BACKEND_DIR="${BACKEND_DIR:-$ROOT/backend}"
API_PORT="${API_PORT:-8765}"
PG_PORT="${PG_PORT:-55432}"
REDIS_PORT="${REDIS_PORT:-56379}"
API_KEY="acg_live_TEST_E2E_KEY_DO_NOT_USE_IN_PROD"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}→${NC} $1"; }

teardown() {
    info "Stopping services..."
    docker rm -f acg_pg acg_redis 2>/dev/null || true
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    rm -rf /tmp/acg_test_venv 2>/dev/null || true
    pass "Teardown complete"
}

if [[ "${1:-}" == "--teardown" ]]; then teardown; exit 0; fi

trap 'echo; info "Test interrupted — run ./test_e2e.sh --teardown to clean up"' INT TERM

info "Pre-flight: checking prerequisites"
command -v docker >/dev/null || fail "docker not installed"
command -v python3 >/dev/null || fail "python3 not installed"
command -v curl >/dev/null || fail "curl not installed"
command -v jq >/dev/null || fail "jq not installed (brew install jq)"
[[ -d "$SDK_DIR" ]] || fail "SDK dir not found: $SDK_DIR"
[[ -d "$BACKEND_DIR" ]] || fail "Backend dir not found: $BACKEND_DIR"
pass "Prerequisites OK"

info "Test 1: SDK installs and imports"
python3 -m venv /tmp/acg_test_venv
# shellcheck source=/dev/null
source /tmp/acg_test_venv/bin/activate
pip install -q --upgrade pip
pip install -q -e "$SDK_DIR[dev]"
python3 -c "import agentcogs; assert agentcogs.__version__, 'no version'" \
    || fail "SDK import failed"
pass "Test 1: SDK installs (v$(python3 -c 'import agentcogs; print(agentcogs.__version__)'))"

info "Test 2: SDK unit tests"
(cd "$SDK_DIR" && pytest -q tests/) || fail "pytest failed"
pass "Test 2: All SDK unit tests pass"

info "Test 3: Anthropic cache token fix"
python3 <<'EOF' || fail "Anthropic cache fix failed"
from agentcogs.tokens import normalize_summary
out = normalize_summary({
    "claude-3-5-sonnet": {
        "input_tokens": 500,
        "cache_read_input_tokens": 8000,
        "cache_creation_input_tokens": 200,
        "output_tokens": 100,
        "cost": 0.025,
    }
})
assert out["claude-3-5-sonnet"]["input_tokens"] == 8700, \
    f"expected 8700, got {out['claude-3-5-sonnet']['input_tokens']}"
print("OK")
EOF
pass "Test 3: Anthropic cache tokens correctly summed (8700, not 500)"

info "Test 4: SDK offline mode (no backend required)"
python3 <<'EOF' || fail "offline mode failed"
import agentcogs
agentcogs.init(offline=True, workspace_id="ws_test")
with agentcogs.run(customer_id="cust_offline"):
    pass
print("OK")
EOF
pass "Test 4: SDK offline mode works"

info "Test 5: Booting Postgres + Redis via Docker"
docker rm -f acg_pg acg_redis 2>/dev/null || true

docker run -d --name acg_pg \
    -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=agentcogs \
    -p "$PG_PORT:5432" postgres:16 >/dev/null

docker run -d --name acg_redis \
    -p "$REDIS_PORT:6379" redis:7-alpine >/dev/null

info "Waiting for Postgres..."
for i in $(seq 1 30); do
    if docker exec acg_pg pg_isready -U postgres >/dev/null 2>&1; then break; fi
    sleep 1
    [[ $i -eq 30 ]] && fail "Postgres did not start"
done

info "Waiting for Redis..."
for i in $(seq 1 15); do
    if docker exec acg_redis redis-cli ping >/dev/null 2>&1; then break; fi
    sleep 1
    [[ $i -eq 15 ]] && fail "Redis did not start"
done
pass "Test 5: Postgres + Redis up"

info "Test 6: Running schema migration"
DB_URL="postgresql://postgres:dev@localhost:$PG_PORT/agentcogs"
docker exec -i acg_pg psql -U postgres -d agentcogs < \
    "$BACKEND_DIR/migrations/versions/001_init.sql" >/dev/null
docker exec -i acg_pg psql -U postgres -d agentcogs < \
    "$BACKEND_DIR/migrations/versions/002_onboarding.sql" >/dev/null 2>&1 || true
docker exec -i acg_pg psql -U postgres -d agentcogs < \
    "$BACKEND_DIR/migrations/versions/003_api_key_hash.sql" >/dev/null
docker exec acg_pg psql -U postgres -d agentcogs -c "
    INSERT INTO workspaces (name, email, api_key, plan)
    VALUES ('Test Co', 'test@e2e.com', '$API_KEY', 'free');
" >/dev/null
docker exec -i acg_pg psql -U postgres -d agentcogs < \
    "$BACKEND_DIR/migrations/versions/003_api_key_hash.sql" >/dev/null
WS_ID=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT id FROM workspaces WHERE api_key='$API_KEY'")
[[ -n "$WS_ID" ]] || fail "Could not create workspace"
pass "Test 6: Schema + workspace created (id=$WS_ID)"

info "Test 7: Booting FastAPI backend"
cd "$BACKEND_DIR"
pip install -q -e . >/dev/null 2>&1 || fail "Backend deps install failed"

DATABASE_URL="$DB_URL" \
REDIS_URL="redis://localhost:$REDIS_PORT" \
JWT_SECRET="e2e-test-secret" \
CORS_ORIGINS="http://localhost:5173" \
ENVIRONMENT="test" \
    uvicorn app.main:app --port "$API_PORT" --log-level warning &
API_PID=$!
cd - >/dev/null

info "Waiting for backend health check..."
for i in $(seq 1 20); do
    if curl -s "http://localhost:$API_PORT/health" >/dev/null 2>&1; then break; fi
    sleep 1
    [[ $i -eq 20 ]] && fail "Backend did not start (pid=$API_PID)"
done
HEALTH=$(curl -s "http://localhost:$API_PORT/health")
[[ "$HEALTH" == '{"status":"ok"}' ]] || fail "Bad health response: $HEALTH"
pass "Test 7: Backend up at :$API_PORT"

info "Test 7b: GET /v1/sdk/ping"
PING_RESP=$(curl -s "http://localhost:$API_PORT/v1/sdk/ping" \
    -H "Authorization: Bearer $API_KEY")
echo "$PING_RESP" | jq -e '.ok == true' >/dev/null \
    || fail "SDK ping failed: $PING_RESP"
pass "Test 7b: SDK ping OK"

info "Test 7c: GET /health/ready"
READY_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$API_PORT/health/ready")
[[ "$READY_CODE" == "200" ]] || fail "health/ready returned $READY_CODE"
pass "Test 7c: health/ready OK"

info "Test 8: POST /v1/ingest"
RUN_ID="00000000-0000-0000-0000-000000000001"
TS=$(date +%s)
INGEST_RESP=$(curl -s -X POST "http://localhost:$API_PORT/v1/ingest" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
        \"run_id\": \"$RUN_ID\",
        \"workspace_id\": \"ignored\",
        \"customer_id\": \"cust_e2e\",
        \"workflow_id\": \"smoke\",
        \"ts\": $TS,
        \"status\": \"completed\",
        \"total_usd\": 0.0042,
        \"models\": {\"gpt-4o-mini\": {\"input_tokens\": 100, \"output_tokens\": 50, \"usd\": 0.0042}},
        \"node_costs\": {\"plan\": 0.001, \"execute\": 0.0032}
    }")
echo "$INGEST_RESP" | jq -e '.accepted == true' >/dev/null \
    || fail "Ingest rejected: $INGEST_RESP"
pass "Test 8: Ingest accepted"

ROW_COUNT=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT COUNT(*) FROM cost_events WHERE id='$RUN_ID'")
[[ "$ROW_COUNT" == "1" ]] || fail "Event not in Postgres (count=$ROW_COUNT)"
pass "Test 8a: Event landed in Postgres"

CUST_ID=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT id FROM customers WHERE external_id='cust_e2e'")
MONTH=$(date -u +%Y-%m)
REDIS_USD=$(docker exec acg_redis redis-cli \
    HGET "spend:ws_${WS_ID}:cust_${CUST_ID}:${MONTH}" usd)
[[ -n "$REDIS_USD" ]] || fail "Redis counter empty"
pass "Test 8b: Redis counter = \$$REDIS_USD"

info "Test 9: Idempotency — re-POST same run_id"
DUP_RESP=$(curl -s -X POST "http://localhost:$API_PORT/v1/ingest" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
        \"run_id\": \"$RUN_ID\",
        \"workspace_id\": \"x\", \"customer_id\": \"cust_e2e\",
        \"workflow_id\": \"smoke\", \"ts\": $TS,
        \"status\": \"completed\", \"total_usd\": 0.0042,
        \"models\": {}, \"node_costs\": {}
    }")
echo "$DUP_RESP" | jq -e '.duplicate == true' >/dev/null \
    || fail "Duplicate not detected: $DUP_RESP"

ROW_COUNT_AFTER=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT COUNT(*) FROM cost_events WHERE id='$RUN_ID'")
[[ "$ROW_COUNT_AFTER" == "1" ]] || fail "Duplicate inserted (count=$ROW_COUNT_AFTER)"

REDIS_USD_AFTER=$(docker exec acg_redis redis-cli \
    HGET "spend:ws_${WS_ID}:cust_${CUST_ID}:${MONTH}" usd)
[[ "$REDIS_USD_AFTER" == "$REDIS_USD" ]] \
    || fail "Counter double-incremented ($REDIS_USD → $REDIS_USD_AFTER)"
pass "Test 9: Duplicate run_id correctly rejected, counter unchanged"

info "Test 10: Budget check (no cap configured)"
BUDGET_RESP=$(curl -s "http://localhost:$API_PORT/v1/budget?workspace=x&customer=cust_e2e" \
    -H "Authorization: Bearer $API_KEY")
echo "$BUDGET_RESP" | jq -e '.status == "ok"' >/dev/null \
    || fail "Expected ok, got: $BUDGET_RESP"
pass "Test 10: Budget returns ok when no cap set"

info "Test 11: Budget enforcement (set cap below current spend)"
docker exec acg_pg psql -U postgres -d agentcogs -c \
    "UPDATE customers SET monthly_budget_usd = 0.001 WHERE external_id = 'cust_e2e'" >/dev/null
docker exec acg_redis redis-cli DEL "cust:${WS_ID}:cust_e2e" >/dev/null

EX_RESP=$(curl -s "http://localhost:$API_PORT/v1/budget?workspace=x&customer=cust_e2e" \
    -H "Authorization: Bearer $API_KEY")
echo "$EX_RESP" | jq -e '.status == "exceeded"' >/dev/null \
    || fail "Expected exceeded, got: $EX_RESP"
pass "Test 11: Budget correctly reports exceeded"

info "Test 12: SDK posts to live backend"
docker exec acg_pg psql -U postgres -d agentcogs -c \
    "UPDATE customers SET monthly_budget_usd = NULL WHERE external_id = 'cust_e2e'" >/dev/null
docker exec acg_redis redis-cli DEL "cust:${WS_ID}:cust_e2e" >/dev/null

AGENTCOGS_API_KEY="$API_KEY" \
AGENTCOGS_WORKSPACE_ID="$WS_ID" \
AGENTCOGS_ENDPOINT="http://localhost:$API_PORT" \
python3 <<'EOF' || fail "SDK integration failed"
import time
import agentcogs
from unittest.mock import patch

agentcogs.init()

class FakeCtx:
    def summary_data(self):
        return {
            "total_cost": 0.0123,
            "by_model": {
                "gpt-4o-mini": {"input_tokens": 200, "output_tokens": 80, "cost": 0.0123}
            },
        }

class FakeShekelBudget:
    def __init__(self, **kw):
        pass

    def __enter__(self):
        return FakeCtx()

    def __exit__(self, *a):
        return False

with patch("agentcogs.budget.shekel_budget", FakeShekelBudget):
    with agentcogs.run(customer_id="cust_sdk_integration", workflow_id="integration"):
        pass

time.sleep(2)
print("OK")
EOF

SDK_COUNT=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT COUNT(*) FROM cost_events e JOIN customers c ON c.id=e.customer_id
     WHERE c.external_id='cust_sdk_integration'")
[[ "$SDK_COUNT" -ge 1 ]] || fail "SDK event not in DB (count=$SDK_COUNT)"
pass "Test 12: SDK → backend → Postgres works end-to-end"

info "Test 13: Leaderboard query (raw SQL — endpoint needs JWT)"
LB_ROWS=$(docker exec acg_pg psql -U postgres -d agentcogs -tAc \
    "SELECT COUNT(*) FROM customers WHERE workspace_id='$WS_ID'")
[[ "$LB_ROWS" -ge 2 ]] || fail "Expected ≥2 customers, got $LB_ROWS"
pass "Test 13: $LB_ROWS customers in leaderboard"

info "Test 14: Bad API key returns 401"
BAD_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:$API_PORT/v1/ingest" \
    -H "Authorization: Bearer not_a_real_key" \
    -H "Content-Type: application/json" \
    -d '{"run_id":"00000000-0000-0000-0000-000000000099","workspace_id":"x","customer_id":"x","ts":0,"status":"completed","total_usd":0}')
[[ "$BAD_RESP" == "401" ]] || fail "Expected 401, got $BAD_RESP"
pass "Test 14: Bad API key rejected (401)"

info "All tests passed — shutting down"
kill $API_PID 2>/dev/null || true
docker rm -f acg_pg acg_redis >/dev/null 2>&1

echo
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ALL 14 E2E TESTS PASSED ✓${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo
echo "Next steps:"
echo "  1. Send your 5 Week-0 DMs (if you haven't)"
echo "  2. Deploy backend to Railway (push to main)"
echo "  3. Deploy dashboard to Vercel (push to main)"
echo "  4. Publish SDK to PyPI:  cd $SDK_DIR && python -m build && twine upload dist/*"
echo
