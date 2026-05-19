#!/usr/bin/env bash
# Start demo stack without re-seeding (~10 seconds).
# Backend + dashboard run as detached daemons (survive terminal close).
#
# Usage:  ./tools/start_demo.sh
# Stop:   ./tools/stop_demo.sh
# Seed:   ./tools/seed_demo.sh   (first time or reset data)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/tools/demo_daemon.sh"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${YELLOW}→${NC} $1"; }

if [[ ! -f "$ROOT/tools/.demo_env" ]]; then
  echo "No demo data found. Run ./tools/seed_demo.sh first (~2-3 min)."
  exit 1
fi

info "Docker (Postgres + Redis)"
demo_ensure_docker
pass "Postgres + Redis up"

info "Backend API :$(demo_api_port)"
demo_start_backend
pass "Backend healthy"

info "Dashboard :$(demo_web_port)"
(cd "$ROOT/dashboard" && demo_start_dashboard)
pass "Dashboard up"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Demo stack ready"
echo "═══════════════════════════════════════════════════"
echo ""
demo_print_status
echo ""
echo "Verify:  ./tools/verify_demo.sh"
echo "Stop:    ./tools/stop_demo.sh"
echo ""
