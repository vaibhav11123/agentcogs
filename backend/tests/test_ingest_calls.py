"""Ingest stores the airport split once, and a changed bill is rejected."""

from __future__ import annotations

import copy
import json
import os
import time
import uuid
from pathlib import Path

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if (not DATABASE_URL or not REDIS_URL) and not os.environ.get("GITHUB_ACTIONS"):
    pytest.skip("DATABASE_URL and REDIS_URL are required", allow_module_level=True)
if (not DATABASE_URL or not REDIS_URL) and os.environ.get("GITHUB_ACTIONS"):
    pytest.fail("DATABASE_URL and REDIS_URL are required in GitHub Actions")

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "kernel"
VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"
API_KEY = "acg_live_ledgerkernel"


def _airport() -> dict:
    cases = json.loads((FIXTURES / "allocate_v1.json").read_text())["cases"]
    return next(case for case in cases if case["id"] == "airport-two-calls")


async def _reset() -> None:
    import asyncpg

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("DROP SCHEMA public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        for path in sorted(VERSIONS.glob("*.sql")):
            await conn.execute(path.read_text())
        from app.auth import hash_api_key

        ws = await conn.fetchval(
            """
            INSERT INTO workspaces (name, email, api_key, plan)
            VALUES ('Ledger', 'ledger@example.com', $1, 'pro')
            RETURNING id
            """,
            API_KEY,
        )
        await conn.execute(
            """
            INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
            VALUES ($1, $2, $3)
            """,
            ws,
            hash_api_key(API_KEY),
            API_KEY[-4:],
        )
    finally:
        await conn.close()


@pytest.fixture
async def ledger_app():
    from app.cache import create_redis
    from app.config import settings
    from app.db import create_pool
    from app.main import app

    settings.database_url = DATABASE_URL
    settings.redis_url = REDIS_URL
    await _reset()
    app.state.db = await create_pool()
    app.state.redis = create_redis()
    yield app
    await app.state.db.close()
    await app.state.redis.aclose()


def _body(run_id: str, total: float, case: dict) -> dict:
    return {
        "run_id": run_id,
        "customer_id": "vellum",
        "workflow_id": "support",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": total,
        "book_id": "fixture-v1",
        "calls": copy.deepcopy(case["calls"]),
        "segments": copy.deepcopy(case["segments"]),
    }


@pytest.mark.asyncio
async def test_airport_is_stored_once_and_a_different_bill_is_rejected(ledger_app):
    from httpx import ASGITransport, AsyncClient

    from app.services.admission import spent_micro

    app = ledger_app
    case = _airport()
    run_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {API_KEY}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/v1/ingest", headers=headers, json=_body(run_id, 0.00615, case))
        assert first.status_code == 202, first.text
        second = await client.post("/v1/ingest", headers=headers, json=_body(run_id, 0.00615, case))
        assert second.status_code == 202, second.text
        assert second.json()["duplicate"] is True
        cust = await app.state.db.fetchval("SELECT id FROM customers WHERE external_id = 'vellum'")
        ws = await app.state.db.fetchval("SELECT id FROM workspaces WHERE email = 'ledger@example.com'")
        from datetime import datetime, timezone

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        assert await spent_micro(app.state.redis, str(ws), str(cust), month) == 6150
        changed = await client.post("/v1/ingest", headers=headers, json=_body(run_id, 0.00999, case))
        assert changed.status_code == 409
        assert changed.json()["detail"] == "PAYLOAD_MISMATCH"
        assert await spent_micro(app.state.redis, str(ws), str(cust), month) == 6150
        bare = str(uuid.uuid4())
        without = await client.post(
            "/v1/ingest",
            headers=headers,
            json={
                "run_id": bare,
                "customer_id": "vellum",
                "ts": int(time.time()),
                "status": "completed",
                "total_usd": 0.01,
            },
        )
        assert without.status_code == 202, without.text

    fact = await app.state.db.fetchrow(
        "SELECT calls, incurred_micro FROM ledger_facts WHERE run_id = $1",
        run_id,
    )
    calls = fact["calls"]
    if isinstance(calls, str):
        calls = json.loads(calls)
    by_id = {call["call_id"]: call["incurred_micro"] for call in calls}
    assert by_id["planner"] == 4800
    assert by_id["synthesize"] == 1350
    allocated = await app.state.db.fetchval(
        "SELECT COALESCE(SUM(micro), 0) FROM allocation_lines WHERE run_id = $1",
        run_id,
    )
    assert int(allocated) == 6150
    facts_for_bare = await app.state.db.fetchval(
        "SELECT COUNT(*) FROM ledger_facts WHERE run_id = $1",
        bare,
    )
    assert facts_for_bare == 0


@pytest.mark.asyncio
async def test_lane_mismatch_and_heartbeat(ledger_app):
    from datetime import datetime, timedelta, timezone

    from httpx import ASGITransport, AsyncClient

    app = ledger_app
    case = _airport()
    headers = {"Authorization": f"Bearer {API_KEY}"}
    body = _body(str(uuid.uuid4()), 0.00615, case)
    body["calls"][0]["provider_input_tokens"] = 1
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        mismatch = await client.post("/v1/ingest", headers=headers, json=body)
        assert mismatch.status_code == 422
        assert mismatch.json()["detail"] == "LANE_MISMATCH"
        omitted = _body(str(uuid.uuid4()), 0.00615, case)
        ok = await client.post("/v1/ingest", headers=headers, json=omitted)
        assert ok.status_code == 202, ok.text
        beat = await client.post("/v1/heartbeat", headers=headers, json={"oldest_outbox_age_sec": 10})
        assert beat.status_code == 200, beat.text
        first = datetime.fromisoformat(beat.json()["watermark_event_time"])
        if first.tzinfo is None:
            first = first.replace(tzinfo=timezone.utc)
        again = await client.post("/v1/heartbeat", headers=headers, json={"oldest_outbox_age_sec": 1000})
        second = datetime.fromisoformat(again.json()["watermark_event_time"])
        if second.tzinfo is None:
            second = second.replace(tzinfo=timezone.utc)
        assert second == first
        assert first <= datetime.now(timezone.utc) - timedelta(seconds=300)
