"""A provider difference is stored. Allocation bytes are not rewritten."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

from app.jobs.provider_residual import record_drift, record_residual, write_residual

ALLOCATION = b'{"planner":1875,"synthesize":1875}'


def test_residual_and_drift_leave_the_allocation_alone():
    before = bytes(ALLOCATION)
    assert record_residual(1_000_000_000, 1_030_000_000) == 30_000_000
    assert record_residual(1_000_000_000, None) is None
    drift = record_drift(100, 90)
    assert drift["ledger_micro"] == 100
    assert drift["redis_micro"] == 90
    assert ALLOCATION == before


def test_closed_day_writes_one_row_and_an_open_day_does_not():
    import asyncio

    async def body() -> None:
        db = AsyncMock()
        today = date(2026, 11, 25)
        closed = today - timedelta(days=2)

        async def fetch():
            return 1_030_000_000

        residual = await write_residual(db, "ws", "openai", closed, 1_000_000_000, fetch, today)
        assert residual == 30_000_000
        assert db.execute.await_count == 1
        assert await write_residual(db, "ws", "openai", today, 1, fetch, today) is None
        assert db.execute.await_count == 1
        assert ALLOCATION == b'{"planner":1875,"synthesize":1875}'

    asyncio.run(body())
