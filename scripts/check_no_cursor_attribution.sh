#!/usr/bin/env bash
# CI: fail if any commit in range contains Cursor co-author trailers.
set -euo pipefail
RANGE="${1:-HEAD}"
BAD=0
while read -r sha; do
  [ -z "$sha" ] && continue
  if git log -1 --format='%B' "$sha" | rg -qi 'Co-authored-by:.*cursor|Made with Cursor|Generated with Cursor'; then
    echo "FAIL: $sha has Cursor/agent attribution:"
    git log -1 --oneline "$sha"
    BAD=1
  fi
done < <(git rev-list "$RANGE" 2>/dev/null)
if [ "$BAD" -ne 0 ]; then
  exit 1
fi
echo "OK: no Cursor attribution in $RANGE"
