"""Admission lease against real Redis. Lua is not reimplemented here."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import pytest

REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if not REDIS_URL and not os.environ.get("GITHUB_ACTIONS"):
    pytest.skip("REDIS_URL is unset", allow_module_level=True)
if not REDIS_URL and os.environ.get("GITHUB_ACTIONS"):
    pytest.fail("REDIS_URL is required in GitHub Actions")

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "kernel"


def test_reserve_matches_vectors_and_settle_is_once():
    import redis.asyncio as redis_async

    from app.services.admission import keys_for, reserve, settle, spent_micro

    async def body() -> None:
        client = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            cases = json.loads((FIXTURES / "admit_v1.json").read_text())["cases"]
            for case in cases:
                ws = str(uuid.uuid4())
                cust = str(uuid.uuid4())
                found = keys_for(ws, cust, "2026-11")
                await client.delete(found["spent"], found["holds"], found["exp"])
                if case["spent"]:
                    await client.set(found["spent"], case["spent"])
                if case["held"]:
                    await client.hset(found["holds"], "prior", case["held"])
                    await client.zadd(found["exp"], {"prior": int(time.time()) + 600})
                decision = await reserve(
                    client,
                    ws,
                    cust,
                    "probe",
                    case["estimate"],
                    300,
                    case["budget"],
                    month="2026-11",
                )
                assert decision == case["decision"], case["id"]

            ws = str(uuid.uuid4())
            cust = str(uuid.uuid4())
            run_id = str(uuid.uuid4())
            assert await settle(client, ws, cust, run_id, 6150, month="2026-11") == 1
            assert await spent_micro(client, ws, cust, "2026-11") == 6150
            assert await settle(client, ws, cust, run_id, 6150, month="2026-11") == 0
            assert await spent_micro(client, ws, cust, "2026-11") == 6150
        finally:
            await client.aclose()

    asyncio.run(body())


def test_expired_hold_is_dropped_inside_reserve():
    import redis.asyncio as redis_async

    from app.services.admission import keys_for, reserve

    async def body() -> None:
        client = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            ws = str(uuid.uuid4())
            cust = str(uuid.uuid4())
            await reserve(client, ws, cust, "hold-me", 50, 1, 1000, month="2026-11")
            time.sleep(1.1)
            await reserve(client, ws, cust, "next", 10, 300, 1000, month="2026-11")
            found = keys_for(ws, cust, "2026-11")
            held = await client.hgetall(found["holds"])
            assert "hold-me" not in held
        finally:
            await client.aclose()

    asyncio.run(body())
