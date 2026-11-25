"""A crashed settle is repaired without another client request."""

from __future__ import annotations

import asyncio
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


def test_reconcile_rebuilds_redis_and_drops_an_abandoned_hold():
    import asyncpg
    import redis.asyncio as redis_async

    from app.jobs.reconcile import reconcile
    from app.services.admission import keys_for, reserve, spent_micro

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


def test_reconcile_does_not_overwrite_a_settle_that_lands_after_the_sum():
    import asyncpg
    import redis.asyncio as redis_async
    from datetime import datetime, timezone

    from app.jobs.reconcile import reconcile
    from app.services.admission import settle, spent_micro

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
            now = datetime.now(timezone.utc)
            month = datetime(now.year, now.month, 1, tzinfo=timezone.utc).date()
            first = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO ledger_facts
                  (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                VALUES ($1, $2, $3, $4, 'fixture-v1', 6150)
                """,
                ws, first, cust, now,
            )
            await conn.execute(
                """
                INSERT INTO settlement_receipts
                  (workspace_id, run_id, customer_id, month, actual_micro)
                VALUES ($1, $2, $3, $4, 6150)
                """,
                ws, first, cust, month,
            )
            await client.flushdb()
            await reconcile(conn, client)
            assert await spent_micro(client, str(ws), str(cust)) == 6150

            started = asyncio.Event()
            release = asyncio.Event()

            async def pause() -> None:
                started.set()
                await release.wait()

            second = uuid.uuid4()
            task = asyncio.create_task(reconcile(conn, client, pause_after_sum=pause))
            await started.wait()
            await conn.execute(
                """
                INSERT INTO ledger_facts
                  (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                VALUES ($1, $2, $3, $4, 'fixture-v1', 1000)
                """,
                ws, second, cust, now,
            )
            await conn.execute(
                """
                INSERT INTO settlement_receipts
                  (workspace_id, run_id, customer_id, month, actual_micro)
                VALUES ($1, $2, $3, $4, 1000)
                """,
                ws, second, cust, month,
            )
            await settle(client, str(ws), str(cust), str(second), 1000)
            release.set()
            await task
            stored = await conn.fetchval(
                "SELECT COALESCE(SUM(actual_micro), 0)::bigint FROM settlement_receipts WHERE customer_id = $1",
                cust,
            )
            assert int(stored) == 7150
            assert await spent_micro(client, str(ws), str(cust)) == 7150
        finally:
            await client.aclose()
            await conn.close()

    asyncio.run(body())


def test_restored_total_keeps_the_settlement_marker():
    import asyncpg
    import redis.asyncio as redis_async
    from datetime import datetime, timezone

    from app.jobs.reconcile import reconcile
    from app.services.admission import keys_for, settle, spent_micro

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
            now = datetime.now(timezone.utc)
            month = datetime(now.year, now.month, 1, tzinfo=timezone.utc).date()
            run_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO ledger_facts
                  (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                VALUES ($1, $2, $3, $4, 'fixture-v1', 6150)
                """,
                ws, run_id, cust, now,
            )
            await conn.execute(
                """
                INSERT INTO settlement_receipts
                  (workspace_id, run_id, customer_id, month, actual_micro)
                VALUES ($1, $2, $3, $4, 6150)
                """,
                ws, run_id, cust, month,
            )
            await client.flushdb()
            await reconcile(conn, client)
            found = keys_for(str(ws), str(cust), now.strftime("%Y-%m"), str(run_id))
            assert await client.get(found["settled"]) == "1"
            await settle(client, str(ws), str(cust), str(run_id), 6150)
            assert await spent_micro(client, str(ws), str(cust)) == 6150
        finally:
            await client.aclose()
            await conn.close()

    asyncio.run(body())


def test_budget_counts_a_committed_run_before_its_receipt():
    import asyncpg
    from datetime import datetime, timezone
    from decimal import Decimal

    from app.routes import budget as budget_route

    versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"

    async def body() -> None:
        conn = await asyncpg.connect(DATABASE_URL)
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
            now = datetime.now(timezone.utc)
            run_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO cost_events
                  (id, workspace_id, customer_id, workflow_id, ts, status, total_usd)
                VALUES ($1, $2, $3, 'default', $4, 'completed', 0.006150)
                """,
                run_id, ws, cust, now,
            )
            await conn.execute(
                """
                INSERT INTO ledger_facts
                  (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                VALUES ($1, $2, $3, $4, 'fixture-v1', 6150)
                """,
                ws, run_id, cust, now,
            )
            budget_route._pg_cache.clear()
            spent = await budget_route._spent_from_postgres(conn, str(ws), str(cust))
            assert spent == Decimal("0.006150")
        finally:
            await conn.close()

    asyncio.run(body())
