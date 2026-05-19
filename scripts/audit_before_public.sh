#!/usr/bin/env bash
# Pre-flight checks before making the GitHub repo public. Exit 1 on any failure.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0

echo "== AgentCOGS public-repo audit =="

echo "[1/6] Tracked .env / credential files"
if git ls-files | rg -q '^\.env$|/\.env$|\.pem$|\.key$|tools/\.demo_env'; then
  echo "FAIL: sensitive paths are tracked in git"
  git ls-files | rg '\.env$|\.pem$|\.key$|tools/\.demo_env' || true
  FAIL=1
else
  echo "OK: no .env / .pem / .demo_env in index"
fi

echo "[2/6] tools/.demo_env must stay gitignored"
if git check-ignore -q tools/.demo_env 2>/dev/null; then
  echo "OK: tools/.demo_env is gitignored"
else
  echo "FAIL: add tools/.demo_env to .gitignore"
  FAIL=1
fi

echo "[3/6] Obvious secret literals in tracked files (heuristic)"
# Placeholders like acg_live_... and TEST keys are allowed; flag likely real keys.
if git grep -E 'sk-ant-api[0-9A-Za-z_-]{20,}|sk_live_[0-9A-Za-z]{20,}|re_[0-9A-Za-z]{20,}|ghp_[0-9A-Za-z]{20,}' -- ':!*.lock' 2>/dev/null; then
  echo "FAIL: possible real API key in repo"
  FAIL=1
else
  echo "OK: no sk-ant-api / sk_live / re_ / ghp_ patterns in tracked files"
fi

echo "[4/6] Local secret files present on disk (informational)"
for f in .env backend/.env dashboard/.env tools/.demo_env; do
  if [[ -f "$f" ]]; then
    echo "  note: $f exists locally (must not be committed)"
  fi
done

echo "[5/6] docs/internal/ (review before publish)"
if [[ -d docs/internal ]]; then
  ls -1 docs/internal/
else
  echo "  (no docs/internal/)"
fi

echo "[6/6] Run tests (optional: SKIP_TESTS=1)"
if [[ "${SKIP_TESTS:-}" == "1" ]]; then
  echo "SKIP: tests"
else
  if command -v pytest >/dev/null 2>&1; then
    pytest -q tests/ backend/tests/ 2>/dev/null || { echo "FAIL: pytest"; FAIL=1; }
  else
    echo "SKIP: pytest not in PATH"
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo ""
  echo "Audit FAILED — fix issues before: gh repo edit --visibility public"
  exit 1
fi
echo ""
echo "Audit passed. Safe to proceed with visibility change after you review docs/internal/."
