#!/usr/bin/env python3
"""Price one OpenAI call and one Anthropic call without leaving the machine.

The clients talk to the mimic in this repository. The posted total is the
fixture book, not a provider invoice.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from mimic_providers import ProviderMimic  # noqa: E402

import agentcogs  # noqa: E402


def main() -> None:
    from anthropic import Anthropic
    from openai import OpenAI

    server = ProviderMimic()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    agentcogs.init(
        api_key="acg_live_MIMIC",
        workspace_id="ws_mimic",
        endpoint=server.origin,
        register_atexit=False,
    )
    try:
        with agentcogs.run(customer_id="customer_001", workflow_id="priced-demo") as ctx:
            OpenAI(api_key="sk-mimic", base_url=f"{server.origin}/v1").chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
            )
            Anthropic(api_key="sk-ant-mimic", base_url=server.origin).messages.create(
                model="claude-3-5-haiku",
                max_tokens=8,
                messages=[{"role": "user", "content": "ping"}],
            )
        event = ctx._event or {}
        openai_lanes = event["calls"][0]["lanes"]
        anthropic_lanes = event["calls"][1]["lanes"]
        print(f"calls {len(event['calls'])}")
        print(f"book {event['book_id']}")
        print(f"total_usd {event['total_usd']}")
        print(
            "openai uncached {uncached_input} cache_read {cache_read} "
            "cache_write_30m {cache_write_30m}".format(**openai_lanes)
        )
        print(
            "anthropic uncached {uncached_input} cache_read {cache_read} "
            "cache_write_5m {cache_write_5m} cache_write_1h {cache_write_1h}".format(**anthropic_lanes)
        )
    finally:
        agentcogs.shutdown()
        server.shutdown()


if __name__ == "__main__":
    main()
