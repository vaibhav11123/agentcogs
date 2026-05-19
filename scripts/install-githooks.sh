#!/usr/bin/env bash
# Install repo githooks into .git/hooks (no git config changes).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
HOOKS_DIR="$ROOT/.git/hooks"
mkdir -p "$HOOKS_DIR"
chmod +x .githooks/commit-msg .githooks/pre-commit
install -m 755 .githooks/commit-msg "$HOOKS_DIR/commit-msg"
install -m 755 .githooks/pre-commit "$HOOKS_DIR/pre-commit"
echo "Installed: $HOOKS_DIR/commit-msg and pre-commit"
