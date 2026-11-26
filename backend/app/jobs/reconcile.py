"""Bring Redis spend back to the sum of settlement receipts.

Runs inside the API process. A client that never retries is still repaired.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..services.admission import keys_for, sweep_holds

log = logging.getLogger("agentcogs.reconcile")


_CAS_SET = """
local current = redis.call('GET', KEYS[1])
if current == false then current = '0' end
if current ~= ARGV[1] then return 0 end
if tonumber(current) > tonumber(ARGV[2]) then return 0 end
redis.call('SET', KEYS[1], ARGV[2])
return 1
"""


async def reconcile(db, redis, pause_after_sum=None) -> dict:
    swept = 0
    pairs = await db.fetch(
        """
        SELECT DISTINCT workspace_id, customer_id
        FROM ledger_facts
        WHERE customer_id IS NOT NULL
        """
    )
    for pair in pairs:
        swept += await sweep_holds(redis, str(pair["workspace_id"]), str(pair["customer_id"]))

    missing = await db.fetch(
        """
        SELECT f.workspace_id, f.run_id, f.customer_id, f.incurred_micro, f.event_time
        FROM ledger_facts f
        LEFT JOIN settlement_receipts r
          ON r.workspace_id = f.workspace_id AND r.run_id = f.run_id
        WHERE r.run_id IS NULL AND f.customer_id IS NOT NULL
        """
    )
    await _insert_receipts(db, missing)
    repaired = await _repair_spent(db, redis, pause_after_sum=pause_after_sum)
    return {"swept": swept, "receipts": len(missing), "repaired": repaired}


def _month_date(when: datetime):
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when, datetime(when.year, when.month, 1, tzinfo=timezone.utc).date()


async def _insert_receipts(db, rows) -> None:
    chunk = 200
    for start in range(0, len(rows), chunk):
        part = rows[start : start + chunk]
        args: list = []
        placeholders: list[str] = []
        index = 1
        for row in part:
            _when, month = _month_date(row["event_time"])
            placeholders.append(f"(${index},${index + 1},${index + 2},${index + 3},${index + 4})")
            args.extend(
                [
                    row["workspace_id"],
                    row["run_id"],
                    row["customer_id"],
                    month,
                    int(row["incurred_micro"]),
                ]
            )
            index += 5
        await db.execute(
            f"""
            INSERT INTO settlement_receipts
              (workspace_id, run_id, customer_id, month, actual_micro)
            VALUES {",".join(placeholders)}
            ON CONFLICT (workspace_id, run_id) DO NOTHING
            """,
            *args,
        )


async def _receipt_groups(db):
    return await db.fetch(
        """
        SELECT workspace_id, customer_id, month, SUM(actual_micro)::bigint AS total
        FROM settlement_receipts
        GROUP BY workspace_id, customer_id, month
        """
    )


async def _mark_receipts(db, redis) -> None:
    """Restore the per-run marker before publishing a total.

    A Redis restart drops both the total and the marker. Setting the total
    alone lets a replay of an already settled run increment it again.
    """
    rows = await db.fetch(
        """
        SELECT workspace_id, customer_id, run_id, month
        FROM settlement_receipts
        """
    )
    chunk = 500
    for start in range(0, len(rows), chunk):
        part = rows[start : start + chunk]
        async with redis.pipeline(transaction=True) as pipe:
            for row in part:
                found = keys_for(
                    str(row["workspace_id"]),
                    str(row["customer_id"]),
                    row["month"].strftime("%Y-%m"),
                    str(row["run_id"]),
                )
                pipe.set(found["settled"], "1", nx=True)
            await pipe.execute()


async def _repair_spent(db, redis, pause_after_sum=None) -> int:
    """Publish receipt sums without erasing a settle that landed after the read."""
    repaired = 0
    paused = False
    for _attempt in range(8):
        groups = await _receipt_groups(db)
        if pause_after_sum is not None and not paused:
            paused = True
            await pause_after_sum()
            continue
        await _mark_receipts(db, redis)
        if not groups:
            return repaired
        keys = []
        expected = []
        for group in groups:
            found = keys_for(
                str(group["workspace_id"]),
                str(group["customer_id"]),
                group["month"].strftime("%Y-%m"),
            )
            keys.append(found["spent"])
            expected.append(int(group["total"]))
        current_raw = await redis.mget(*keys)
        pending = []
        ahead = False
        for group, key, want, raw in zip(groups, keys, expected, current_raw):
            current = int(raw or 0)
            if current == want:
                continue
            if current > want:
                ahead = True
                continue
            pending.append((group, key, str(current), want, current))
        if not pending and not ahead:
            return repaired
        moved = False
        for group, key, observed, want, current in pending:
            wrote = await redis.eval(_CAS_SET, 1, key, observed, str(want))
            if int(wrote or 0) != 1:
                moved = True
                continue
            await db.execute(
                """
                INSERT INTO ledger_drift
                  (workspace_id, month, ledger_micro, redis_micro)
                VALUES ($1, $2, $3, $4)
                """,
                group["workspace_id"],
                group["month"],
                want,
                current,
            )
            repaired += 1
        if not moved and not ahead:
            return repaired
    log.warning("reconcile left redis ahead of the receipt snapshot")
    return repaired
