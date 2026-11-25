#!/usr/bin/env python3
"""Drive the official SDKs at the local provider mimic and check the ledger event.

No call leaves this machine. OpenAI, Anthropic, and Stripe are the mimic.
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from mimic_providers import ANTHROPIC_USAGE, OPENAI_USAGE, ProviderMimic

import agentcogs
from agentcogs._shekel_compat import lanes_from_usage
from agentcogs.kernel.attribute import price_call
from agentcogs.localstore import price_book
from agentcogs.provider_watch import micro_as_usd

RUNS = 160
WORKERS = 32


def _expected_micro(provider: str, usage: dict) -> int:
    lanes = lanes_from_usage(provider, usage)
    _priced, micro = price_call(lanes, price_book())
    return micro


def _one(origin: str, index: int) -> str:
    from anthropic import Anthropic
    from openai import OpenAI

    customer = f"cust_{index % 17}"
    stream = index % 4 == 0
    with agentcogs.run(customer_id=customer, workflow_id="provider-load") as ctx:
        completion = OpenAI(api_key="sk-mimic", base_url=f"{origin}/v1").chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            stream=stream,
        )
        if stream:
            for _chunk in completion:
                pass
        Anthropic(api_key="sk-ant-mimic", base_url=origin).messages.create(
            model="claude-3-5-haiku",
            max_tokens=8,
            messages=[{"role": "user", "content": "ping"}],
        )
    event = ctx._event or {}
    calls = event.get("calls") or []
    if len(calls) != 2:
        raise AssertionError(f"run {index} posted {len(calls)} calls")
    if event.get("book_id") != "fixture-v1":
        raise AssertionError(event.get("book_id"))
    expected = _expected_micro("openai", OPENAI_USAGE) + _expected_micro("anthropic", ANTHROPIC_USAGE)
    if event["total_usd"] != micro_as_usd(expected):
        raise AssertionError(f"run {index} total {event['total_usd']} != {micro_as_usd(expected)}")
    openai_call, anthropic_call = calls
    if openai_call["lanes"]["cache_read"] != 4000 or openai_call["lanes"]["cache_write_30m"] != 3000:
        raise AssertionError(openai_call["lanes"])
    if anthropic_call["lanes"]["cache_read"] != 8000 or anthropic_call["lanes"]["cache_write_1h"] != 80:
        raise AssertionError(anthropic_call["lanes"])
    if openai_call.get("provider_input_tokens") != 12000:
        raise AssertionError(openai_call)
    return customer


def main() -> None:
    server = ProviderMimic()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = server.origin
    agentcogs.init(
        api_key="acg_live_MIMIC",
        workspace_id="ws_mimic",
        endpoint=origin,
        max_ingest_workers=16,
        register_atexit=False,
        timeout_seconds=5,
    )
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_one, origin, i) for i in range(RUNS)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{type(exc).__name__}: {exc}")
    _stripe_round(origin, failures)
    agentcogs.shutdown()
    unique = {item["run_id"] for item in server.ingests}
    print(
        {
            "runs": RUNS,
            "ingests": len(server.ingests),
            "unique_runs": len(unique),
            "openai": server.counts["openai"],
            "anthropic": server.counts["anthropic"],
            "stripe_list": server.counts["stripe_list"],
            "stripe_meter": server.counts["stripe_meter"],
            "failures": len(failures),
        }
    )
    if failures:
        for line in failures[:12]:
            print(line, file=sys.stderr)
        raise SystemExit(1)
    if len(unique) != RUNS or server.counts["openai"] != RUNS or server.counts["anthropic"] != RUNS:
        print("counts did not match the run", file=sys.stderr)
        raise SystemExit(1)
    server.shutdown()
    print("provider load ok")


def _stripe_round(origin: str, failures: list[str]) -> None:
    import stripe
    from stripe._error import InvalidRequestError

    sys.path.insert(0, str(ROOT / "backend"))
    from app.services.stripe_mrr import subscription_monthly_usd
    from app.services.stripe_sync import _meter_already_recorded

    stripe.api_key = "sk_test_mimic"
    stripe.api_base = origin
    try:
        page = stripe.Subscription.list(customer="cus_mock", status="active", limit=100)
        data = page["data"] if "data" in page else list(page.data)
        total = sum(subscription_monthly_usd(sub) for sub in data)
        if total != 50.0:
            failures.append(f"stripe mrr {total}")
        first = stripe.billing.MeterEvent.create(
            event_name="agentcogs_ai_usage",
            payload={"stripe_customer_id": "cus_mock", "value": "12"},
            identifier="acg_load_once",
        )
        if first["identifier"] != "acg_load_once":
            failures.append("meter identifier missing")
        try:
            stripe.billing.MeterEvent.create(
                event_name="agentcogs_ai_usage",
                payload={"stripe_customer_id": "cus_mock", "value": "12"},
                identifier="acg_load_once",
            )
            failures.append("duplicate meter was accepted")
        except InvalidRequestError as exc:
            if not _meter_already_recorded(exc):
                failures.append(f"duplicate meter not recognised: {exc}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"stripe: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
