"""One streamed OpenAI call and one Anthropic call against the local mimic."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from mimic_providers import (
    ANTHROPIC_USAGE,
    OPENAI_USAGE,
    ProviderMimic,
)

import agentcogs
from agentcogs._shekel_compat import lanes_from_usage
from agentcogs.kernel.attribute import price_call
from agentcogs.localstore import price_book
from agentcogs.provider_watch import micro_as_usd


def test_run_prices_mimicked_provider_usage():
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
        with agentcogs.run(customer_id="cust_mimic", workflow_id="mimic") as ctx:
            stream = OpenAI(api_key="sk-mimic", base_url=f"{server.origin}/v1").chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
                stream=True,
            )
            for _chunk in stream:
                pass
            Anthropic(api_key="sk-ant-mimic", base_url=server.origin).messages.create(
                model="claude-3-5-haiku",
                max_tokens=8,
                messages=[{"role": "user", "content": "ping"}],
            )
        event = ctx._event
        assert event is not None
        assert len(event["calls"]) == 2
        assert event["book_id"] == "fixture-v1"
        assert event["calls"][0]["lanes"]["cache_read"] == 4000
        assert event["calls"][0]["lanes"]["uncached_input"] == 5000
        assert event["calls"][1]["lanes"]["cache_write_1h"] == 80
        book = price_book()
        expected = price_call(lanes_from_usage("openai", OPENAI_USAGE), book)[1]
        expected += price_call(lanes_from_usage("anthropic", ANTHROPIC_USAGE), book)[1]
        assert event["total_usd"] == micro_as_usd(expected)
    finally:
        agentcogs.shutdown()
        server.shutdown()
