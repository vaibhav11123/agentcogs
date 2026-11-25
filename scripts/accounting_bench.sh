#!/usr/bin/env bash
# One command: disposable Postgres database, private Redis, API, real SDK.
# No model provider is called. The database is dropped on exit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADMIN_URL="${ADMIN_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:5432/postgres}"
DB_NAME="accounting_bench_$$"
export DATABASE_URL="${DATABASE_URL_BASE:-postgresql://postgres:postgres@127.0.0.1:5432}/$DB_NAME"
export GIT_COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"

cleanup() {
  local status=$?
  if [[ -n "${BENCH_PID:-}" ]]; then
    kill "$BENCH_PID" 2>/dev/null || true
    wait "$BENCH_PID" 2>/dev/null || true
  fi
  psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid()" >/dev/null || true
  psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$DB_NAME\"" >/dev/null || true
  exit "$status"
}
trap cleanup EXIT

psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DB_NAME\"" >/dev/null
for migration in "$ROOT"/backend/migrations/versions/*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration" >/dev/null
done

if [[ "${1:-}" == "--scale" ]]; then
  export ACCOUNTING_BENCH_SCALE=1
  export ACCOUNTING_BENCH_RUNS="${ACCOUNTING_BENCH_RUNS:-100000}"
  export ACCOUNTING_BENCH_CUSTOMERS="${ACCOUNTING_BENCH_CUSTOMERS:-1000}"
  export ACCOUNTING_BENCH_WORKSPACES="${ACCOUNTING_BENCH_WORKSPACES:-10}"
  export ACCOUNTING_BENCH_PASSES="${ACCOUNTING_BENCH_PASSES:-3}"
  export ACCOUNTING_BENCH_HOLD_SECONDS="${ACCOUNTING_BENCH_HOLD_SECONDS:-900}"
  export ACCOUNTING_BENCH_RACES="${ACCOUNTING_BENCH_RACES:-10000}"
  export ACCOUNTING_BENCH_RESULTS="${ACCOUNTING_BENCH_RESULTS:-$ROOT/docs/internal/bench-scale}"
fi

cd "$ROOT"
python3 bench/accounting_bench.py
