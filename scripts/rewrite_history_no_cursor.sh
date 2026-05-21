#!/usr/bin/env bash
# Rewrite main history: strip Cursor co-author trailers and new commit SHAs
# so GitHub drops cursoragent from the Contributors sidebar.
#
# Usage (from repo root):
#   ./scripts/rewrite_history_no_cursor.sh
#   git push --force-with-lease origin main

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "Installing git-filter-repo..."
  pip install -q git-filter-repo
fi

echo "→ Stripping Cursor trailers from messages..."
git filter-repo --force --message-callback '
import re
lines = message.split(b"\n")
out = []
for line in lines:
    if re.match(rb"^Co-authored-by:\s*.*cursor", line, re.I):
        continue
    if line in (b"Made with Cursor", b"Generated with Cursor"):
        continue
    out.append(line)
return b"\n".join(out)
'

echo "→ Bumping commit timestamps (new SHAs for GitHub contributor cache)..."
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter '
  t=$(git log -1 --format=%at)
  export GIT_AUTHOR_DATE="@$((t+1))"
  export GIT_COMMITTER_DATE="@$((t+1))"
' main

echo "→ Re-adding origin remote..."
git remote add origin "https://github.com/vaibhav11123/agentcogs.git" 2>/dev/null || \
  git remote set-url origin "https://github.com/vaibhav11123/agentcogs.git"

echo ""
echo "Done. Push: git push --force-with-lease origin main"
