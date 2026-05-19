#!/usr/bin/env python3
"""Live pipeline: Claude → agentcogs.run() → local backend → Postgres.

Prerequisites:
  ./tools/seed_demo.sh          # once
  ./tools/start_demo.sh         # API on :8000, dashboard on :5173
  export ANTHROPIC_API_KEY=...  # your Claude key

Usage:
  python3 scripts/run_live_pipeline.py
  python3 scripts/run_live_pipeline.py --customer pied_piper
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ENV = ROOT / "tools" / ".demo_env"
# Anthropic Haiku 4.5 list: $1/M input, $5/M output → per 1k for Shekel.
CLAUDE_HAIKU_45_PER_1K = {"input": 0.001, "output": 0.005}


def _load_demo_env() -> None:
    if not DEMO_ENV.is_file():
        sys.exit(
            f"Missing {DEMO_ENV}\n"
            "Run:  ./tools/seed_demo.sh\n"
            "Then: ./tools/start_demo.sh"
        )
    for line in DEMO_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live SDK + Claude against local demo API")
    parser.add_argument(
        "--customer",
        default="pied_piper",
        help="Customer external_id (default pied_piper; avoid acme_corp — over demo budget)",
    )
    parser.add_argument("--workflow", default="claude_live")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("AGENTCOGS_ENDPOINT", "http://localhost:8000"),
    )
    args = parser.parse_args()

    _load_demo_env()

    api_token = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_token:
        sys.exit("Set ANTHROPIC_API_KEY before running this script.")
    if "..." in api_token or api_token.endswith("..."):
        sys.exit(
            "ANTHROPIC_API_KEY looks like a placeholder (contains '...').\n"
            "Export your real key from https://console.anthropic.com/settings/keys"
        )
    os.environ["ANTHROPIC_API_KEY"] = api_token

    api_key = os.environ.get("DEMO_API_KEY")
    workspace_id = os.environ.get("DEMO_WORKSPACE_ID")
    if not api_key or not workspace_id:
        sys.exit(f"{DEMO_ENV} must define DEMO_API_KEY and DEMO_WORKSPACE_ID")

    import agentcogs
    from anthropic import Anthropic

    agentcogs.init(
        api_key=api_key,
        workspace_id=workspace_id,
        endpoint=args.endpoint.rstrip("/"),
    )

    model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
    print(f"→ workspace {workspace_id[:8]}…  customer={args.customer!r}  model={model}")
    print(f"→ endpoint {args.endpoint}")

    client = Anthropic()
    agentcogs.set_customer(args.customer)
    with agentcogs.run(
        workflow_id=args.workflow,
        price_per_1k_tokens=CLAUDE_HAIKU_45_PER_1K,
    ):
        resp = client.messages.create(
            model=model,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hello in one short sentence."}],
        )
        print(f"→ Claude: {resp.content[0].text}")

    time.sleep(2)
    print("✓ Ingest sent (async). Open http://localhost:5173/demo →", args.customer)


if __name__ == "__main__":
    main()
