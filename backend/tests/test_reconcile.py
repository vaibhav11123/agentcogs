"""A crashed settle is repaired without another client request."""

from __future__ import annotations

import asyncio
import os
import time
import uuid

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if (not DATABASE_URL or not REDIS_URL) and not os.environ.get("GITHUB_ACTIONS"):
    pytest.skip("DATABASE_URL and REDIS_URL are required", allow_module_level=True)
if (not DATABASE_URL or not REDIS_URL) and os.environ.get("GITHUB_ACTIONS"):
    pytest.fail("DATABASE_URL and REDIS_URL are required in GitHub Actions")


def test_reconcile_rebuilds_redis_and_drops_an_abandoned_hold():
    import asyncpg
    import redis.asyncio as redis_async

    from app.jobs.reconcile import reconcile
    from app.services.admission import keys_for, reserve, spent_micro
    from pathlib import Path

    versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"

    async def body() -> None:
        conn = await asyncpg.connect(DATABASE_URL)
        client = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            await conn.execute("DROP SCHEMA public CASCADE")
            await conn.execute("CREATE SCHEMA public")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            for path in sorted(versions.glob("*.sql")):
                await conn.execute(path.read_text())
            ws = await conn.fetchval(
                """
                INSERT INTO workspaces (name, email, api_key)
                VALUES ('repair', $1, $2) RETURNING id
                """,
                f"repair-{uuid.uuid4()}@example.com",
                f"acg_live_{uuid.uuid4().hex}",
            )
            cust = await conn.fetchval(
                "INSERT INTO customers (workspace_id, external_id) VALUES ($1, 'c') RETURNING id",
                ws,
            )
            run_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO ledger_facts
                  (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                VALUES ($1, $2, $3, NOW(), 'fixture-v1', 6150)
                """,
                ws,
                run_id,
                cust,
            )
            await reconcile(conn, client)
            assert await spent_micro(client, str(ws), str(cust)) == 6150
            await reconcile(conn, client)
            assert await spent_micro(client, str(ws), str(cust)) == 6150
            month = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m")
            found = keys_for(str(ws), str(cust), month)
            await client.set(found["spent"], 0)
            await reconcile(conn, client)
            assert await spent_micro(client, str(ws), str(cust)) == 6150

            await reserve(client, str(ws), str(cust), "abandoned", 40, 1, 10_000)
            time.sleep(1.1)
            await reconcile(conn, client)
            held = await client.hgetall(found["holds"])
            assert "abandoned" not in held
        finally:
            await client.aclose()
            await conn.close()

    asyncio.run(body())
