"""Bring Redis spend back to the sum of settlement receipts.

Runs inside the API process. A client that never retries is still repaired.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..services.admission import keys_for, month_key, set_spent, settle, sweep_holds

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
    for row in missing:
        when = row["event_time"]
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        month = month_key(when)
        await settle(
            redis,
            str(row["workspace_id"]),
            str(row["customer_id"]),
            str(row["run_id"]),
            int(row["incurred_micro"]),
            month=month,
        )
        await db.execute(
            """
            INSERT INTO settlement_receipts
              (workspace_id, run_id, customer_id, month, actual_micro)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (workspace_id, run_id) DO NOTHING
            """,
            row["workspace_id"],
            row["run_id"],
            row["customer_id"],
            datetime(when.year, when.month, 1, tzinfo=timezone.utc).date(),
            int(row["incurred_micro"]),
        )

    groups = await db.fetch(
        """
        SELECT workspace_id, customer_id, month, SUM(actual_micro)::bigint AS total
        FROM settlement_receipts
        GROUP BY workspace_id, customer_id, month
        """
    )
    repaired = 0
    for group in groups:
        month = group["month"].strftime("%Y-%m")
        found = keys_for(str(group["workspace_id"]), str(group["customer_id"]), month)
        current = int(await redis.get(found["spent"]) or 0)
        expected = int(group["total"])
        if current != expected:
            await db.execute(
                """
                INSERT INTO ledger_drift
                  (workspace_id, month, ledger_micro, redis_micro)
                VALUES ($1, $2, $3, $4)
                """,
                group["workspace_id"],
                group["month"],
                expected,
                current,
            )
            await set_spent(redis, str(group["workspace_id"]), str(group["customer_id"]), month, expected)
            repaired += 1
    return {"swept": swept, "receipts": len(missing), "repaired": repaired}
