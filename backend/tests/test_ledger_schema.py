"""Ledger migration applies twice and the run key is unique. Real Postgres."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL and not os.environ.get("GITHUB_ACTIONS"):
    pytest.skip("DATABASE_URL is unset", allow_module_level=True)
if not DATABASE_URL and os.environ.get("GITHUB_ACTIONS"):
    pytest.fail("DATABASE_URL is required in GitHub Actions")

VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


async def _rebuild(conn) -> None:
    await conn.execute("DROP SCHEMA public CASCADE")
    await conn.execute("CREATE SCHEMA public")
    await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for path in sorted(VERSIONS.glob("*.sql")):
        await conn.execute(path.read_text())
    await conn.execute((VERSIONS / "004_ledger_facts.sql").read_text())


def test_migration_applies_twice_and_run_is_unique():
    import asyncio

    import asyncpg

    async def body() -> None:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await _rebuild(conn)
            rows = await conn.fetch(
                """
                SELECT indexdef FROM pg_indexes
                WHERE tablename = 'ledger_facts' AND indexdef LIKE '%UNIQUE%'
                   OR (tablename = 'ledger_facts' AND indexname LIKE '%pkey%')
                """
            )
            blob = " ".join(row["indexdef"] for row in rows)
            assert "workspace_id" in blob and "run_id" in blob
            ws = await conn.fetchval(
                """
                INSERT INTO workspaces (name, email, api_key)
                VALUES ('ledger', $1, $2) RETURNING id
                """,
                f"ledger-{uuid.uuid4()}@example.com",
                f"acg_live_{uuid.uuid4().hex}",
            )
            cust = await conn.fetchval(
                """
                INSERT INTO customers (workspace_id, external_id)
                VALUES ($1, 'cust') RETURNING id
                """,
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
            with pytest.raises(asyncpg.UniqueViolationError):
                await conn.execute(
                    """
                    INSERT INTO ledger_facts
                      (workspace_id, run_id, customer_id, event_time, book_id, incurred_micro)
                    VALUES ($1, $2, $3, NOW(), 'fixture-v1', 1)
                    """,
                    ws,
                    run_id,
                    cust,
                )
        finally:
            await conn.close()

    asyncio.run(body())
