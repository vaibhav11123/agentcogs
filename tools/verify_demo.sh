#!/usr/bin/env bash
# Post-seed checks for demo data quality (run after seed_demo.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools"
BACKEND="$ROOT/backend"
COMPOSE="docker compose -f $BACKEND/docker-compose.yml"
API_PORT="${API_PORT:-8000}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

# 1. Offline persona/margin simulation
info_msg="Persona margin simulation (seed=42)"
echo "→ $info_msg"
(cd "$TOOLS" && python3 -m pytest tests/test_demo_margins.py tests/test_generate_events.py -q) || fail "$info_msg"

# 2. .demo_env UUID
if [[ -f "$TOOLS/.demo_env" ]]; then
  # shellcheck disable=SC1091
  source "$TOOLS/.demo_env"
  export DEMO_WORKSPACE_ID DEMO_API_KEY DEMO_EMAIL
  [[ "${DEMO_WORKSPACE_ID:-}" =~ ^[0-9a-f-]{36}$ ]] || fail "DEMO_WORKSPACE_ID invalid"
  pass "DEMO_WORKSPACE_ID is valid UUID"
else
  fail "tools/.demo_env missing — run ./tools/seed_demo.sh first"
fi

# 3. API health
curl -sf "http://localhost:$API_PORT/health" >/dev/null || fail "Backend not healthy on :$API_PORT"
pass "Backend healthy"

# 4. Customer count in DB
COUNT=$($COMPOSE exec -T postgres psql -U postgres -d agentcogs -tAc \
  "SELECT COUNT(*) FROM customers WHERE workspace_id='$DEMO_WORKSPACE_ID'::uuid;")
COUNT=$(echo "$COUNT" | tr -d '[:space:]')
[[ "$COUNT" -eq 40 ]] || fail "Expected 40 customers, got $COUNT"
pass "40 customers in database"

# 5. Hero margins from DB (month-to-date)
python3 - <<PY || fail "Hero margin check"
import os, sys, json, urllib.request

ws = os.environ["DEMO_WORKSPACE_ID"]
base = "http://localhost:${API_PORT:-8000}"

# dev-login cookie not needed for demo leaderboard if we query SQL via psql instead
import subprocess
from pathlib import Path

ROOT = Path("${ROOT}")
COMPOSE = "docker compose -f backend/docker-compose.yml"

sql = f"""
SELECT c.external_id, c.monthly_revenue_usd AS rev,
       COALESCE(SUM(e.total_usd), 0) AS cost
FROM customers c
LEFT JOIN cost_events e ON e.customer_id = c.id
  AND e.ts >= date_trunc('month', NOW())
WHERE c.workspace_id = '{ws}'::uuid
  AND c.external_id IN ('acme_corp', 'techflow_inc')
GROUP BY c.external_id, c.monthly_revenue_usd;
"""
out = subprocess.check_output(
    COMPOSE.split() + ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "agentcogs", "-tAc", sql],
    cwd=ROOT,
    text=True,
)
rows = {}
for line in out.strip().splitlines():
    parts = [p.strip() for p in line.split("|")]
    if len(parts) == 3:
        rows[parts[0]] = (float(parts[1]), float(parts[2]))

acme_rev, acme_cost = rows["acme_corp"]
tech_rev, tech_cost = rows["techflow_inc"]
acme_m = (acme_rev - acme_cost) / acme_rev * 100
tech_m = (tech_rev - tech_cost) / tech_rev * 100

print(f"  acme_corp margin={acme_m:.1f}% (target ~75%)")
print(f"  techflow_inc margin={tech_m:.1f}% (target ~29%)")

assert acme_m > tech_m + 20, "Acme should be much healthier than TechFlow"
assert 65 <= acme_m <= 82, f"Acme margin {acme_m:.1f}% out of band"
assert 18 <= tech_m <= 38, f"TechFlow margin {tech_m:.1f}% out of band"
PY
pass "Hero margins in DB match demo script"

# 6. Initech anomaly exists
ANOM=$($COMPOSE exec -T postgres psql -U postgres -d agentcogs -tAc \
  "SELECT COUNT(*) FROM anomalies a JOIN customers c ON c.id=a.customer_id \
   WHERE a.workspace_id='$DEMO_WORKSPACE_ID'::uuid AND c.external_id='initech';")
ANOM=$(echo "$ANOM" | tr -d '[:space:]')
[[ "$ANOM" -ge 1 ]] || fail "No Initech anomalies seeded"
pass "Initech anomaly present ($ANOM)"

echo ""
echo "All demo verification checks passed."
