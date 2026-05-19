#!/usr/bin/env bash
# Deterministic marketing fixture (seed=42).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/marketing/fixtures/screenshot_data.jsonl"
mkdir -p "$(dirname "$OUT")"

pip install -q httpx 2>/dev/null || true

python3 "$ROOT/tools/generate_events.py" \
  --mode file \
  --days 30 \
  --seed 42 \
  --output "$OUT"

echo "✅ Wrote 30 days × 7 personas (seed=42) → $OUT"
echo "   Replay: python3 tools/seed_from_file.py $OUT --api-key KEY --workspace-id WS"
