"""Bring Redis spend back to the sum of settlement receipts.

Runs inside the API process. A client that never retries is still repaired.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..services.admission import keys_for, month_key, sweep_holds

log = logging.getLogger("agentcogs.reconcile")


async def reconcile(db, redis) -> dict:
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
    await _mark_settled(redis, missing)

    groups = await db.fetch(
        """
        SELECT workspace_id, customer_id, month, SUM(actual_micro)::bigint AS total
        FROM settlement_receipts
        GROUP BY workspace_id, customer_id, month
        """
    )
    repaired = await _repair_spent(db, redis, groups)
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


async def _mark_settled(redis, rows) -> None:
    """Mark each repaired run settled so a later ingest does not add it again."""
    chunk = 500
    for start in range(0, len(rows), chunk):
        part = rows[start : start + chunk]
        async with redis.pipeline(transaction=True) as pipe:
            for row in part:
                when, _month = _month_date(row["event_time"])
                found = keys_for(
                    str(row["workspace_id"]),
                    str(row["customer_id"]),
                    month_key(when),
                    str(row["run_id"]),
                )
                pipe.set(found["settled"], "1", nx=True)
            await pipe.execute()


async def _repair_spent(db, redis, groups) -> int:
    if not groups:
        return 0
    keys = []
    expected = []
    for group in groups:
        month = group["month"].strftime("%Y-%m")
        found = keys_for(str(group["workspace_id"]), str(group["customer_id"]), month)
        keys.append(found["spent"])
        expected.append(int(group["total"]))
    current_raw = await redis.mget(*keys)
    repaired = 0
    updates: list[tuple[str, int]] = []
    for group, key, want, raw in zip(groups, keys, expected, current_raw):
        current = int(raw or 0)
        if current == want:
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
        updates.append((key, want))
        repaired += 1
    if updates:
        async with redis.pipeline(transaction=True) as pipe:
            for key, want in updates:
                pipe.set(key, want)
            await pipe.execute()
    return repaired
