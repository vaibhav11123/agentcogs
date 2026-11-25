"""CUSUM fixtures and a count-min bound on a fixed seed."""

from app.kernel.countmin import CountMin
from app.kernel.cusum import cusum_signals, page_kinds


def _series(values: list[int]) -> list[tuple[int, int]]:
    return [(index % 7, value) for index, value in enumerate(values)]


def test_cusum_span_is_not_ready_until_the_oldest_fact_can_cover_a_month():
    from datetime import datetime, timezone

    from app.kernel.cusum import cusum_span_ready

    now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
    assert cusum_span_ready(None, now=now) is False
    assert cusum_span_ready(datetime(2026, 11, 26, 12, tzinfo=timezone.utc), now=now) is False
    assert cusum_span_ready(datetime(2026, 10, 30, tzinfo=timezone.utc), now=now) is False
    assert cusum_span_ready(datetime(2026, 10, 29, 12, tzinfo=timezone.utc), now=now) is True
    assert cusum_span_ready(datetime(2026, 1, 1), now=now) is True


def test_cusum_skips_the_daily_scan_until_the_history_is_long_enough():
    import asyncio
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock

    from app.routes.ingest import check_cusum

    db = AsyncMock()
    db.fetchval = AsyncMock(return_value=datetime.now(timezone.utc))
    db.fetch = AsyncMock()
    db.execute = AsyncMock()

    asyncio.run(check_cusum(db, workspace_id="ws", customer_id="cust", cost_event_id="run"))
    db.fetch.assert_not_called()
    db.execute.assert_not_called()


def test_cusum_inserts_its_own_row_and_does_not_edit_the_zscore():
    import asyncio
    from unittest.mock import AsyncMock
    from datetime import date, datetime, timezone

    from app.routes.ingest import check_cusum

    rows = [{"day": date(2026, 1, 1 + (index % 28)), "micro": 1000} for index in range(30)]
    rows += [{"day": date(2026, 3, 1 + index), "micro": 1_000_000} for index in range(15)]

    class Result:
        def __init__(self, value):
            self.value = value

        def __getitem__(self, key):
            return self.value[key]

    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[Result(row) for row in rows])
    db.fetchval = AsyncMock(side_effect=[datetime(2026, 1, 1, tzinfo=timezone.utc), None])
    db.execute = AsyncMock()

    asyncio.run(check_cusum(db, workspace_id="ws", customer_id="cust", cost_event_id="run"))
    sql = db.execute.await_args.args[0]
    assert "detector" in sql
    assert "'cusum'" in sql
    assert "z_score" not in sql or "NULL" in sql


def test_page_kinds_keeps_both():
    assert page_kinds(True, True) == ["zscore", "cusum"]
    assert page_kinds(True, False) == ["zscore"]
    assert page_kinds(False, True) == ["cusum"]


def test_cusum_level_shift_signals_and_a_spike_does_not():
    shift = _series([1000] * 30 + [1_000_000] * 15)
    assert cusum_signals(shift) is True
    spike = _series([1000] * 30 + [100_000] + [1000] * 14)
    assert cusum_signals(spike) is False
    assert cusum_signals(_series([0] * 5 + [1000] * 30)) is False


def test_count_min_never_underestimates_and_stays_inside_the_bound():
    sketch = CountMin(seed=1)
    sketch.update(7, 1000)
    assert sketch.query(7) >= 1000

    heavy = CountMin(seed=1)
    total = 100_000
    heavy.update(1, 99_000)
    for key in range(2, 21):
        heavy.update(key, 1_000 // 19)
    accounted = 99_000 + (1_000 // 19) * 19
    estimate = heavy.query(1)
    assert estimate >= 99_000
    assert estimate - 99_000 <= 0.001 * total + 1
    assert accounted <= total
