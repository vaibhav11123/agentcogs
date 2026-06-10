#!/usr/bin/env bash
# Run quickstart bash blocks tagged with <!-- verify --> in docs/quickstart.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOC="$ROOT/docs/quickstart.md"
VENV="$(mktemp -d)/venv"
API="${AGENTCOGS_ENDPOINT:-http://localhost:8000}"

python3 -m venv "$VENV"
# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install -q -e "$ROOT[dev]"

export AGENTCOGS_ENDPOINT="$API"

python3 <<'PY'
import re
import subprocess
import sys
from pathlib import Path

doc = Path(sys.argv[1]).read_text()
blocks = re.findall(r"<!-- verify -->\s*```bash\n(.*?)```", doc, re.S)
if not blocks:
    print("No <!-- verify --> bash blocks found — OK (nothing to run)")
    sys.exit(0)

for i, block in enumerate(blocks, 1):
    print(f"Running verified block {i}...")
    subprocess.run(block, shell=True, check=True)
print("All verified quickstart blocks passed")
PY
"$DOC"

deactivate
rm -rf "$(dirname "$VENV")"
