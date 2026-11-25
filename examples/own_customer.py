#!/usr/bin/env python3
"""Record one of your own customers in the local ledger.

Run `agentcogs init` in this directory first. No API key and no server.
The client talks to a stand-in in this repository. The row is priced from
the usage object and stored next to the sample event.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from mimic_providers import ProviderMimic

import agentcogs
from agentcogs.localstore import export_json, ledger_home


def main() -> None:
    from openai import OpenAI

    home = ledger_home()
    if home is None:
        print("Run agentcogs init in this directory first.", file=sys.stderr)
        raise SystemExit(1)
    os.environ.pop("AGENTCOGS_API_KEY", None)
    server = ProviderMimic()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with agentcogs.run(customer_id="acme", workflow_id="support"):
            OpenAI(api_key="sk-mimic", base_url=f"{server.origin}/v1").chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
            )
    finally:
        server.shutdown()
    payload = export_json(home)
    for row in payload["events"]:
        print(f"{row['customer_id']} {row['workflow']} {row['model']} {row['incurred_micro']}")
    print(f"events {payload['status']['events']}")
    print(f"budget_enforce {str(payload['status']['budget_enforce']).lower()}")


if __name__ == "__main__":
    main()
