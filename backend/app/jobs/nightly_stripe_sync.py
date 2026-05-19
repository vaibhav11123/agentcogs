"""Nightly job: push aggregated daily usage to Stripe Meter for each customer.

Run via Railway cron daily at 02:00 UTC:
    python -m app.jobs.nightly_stripe_sync
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import stripe

from app.config import settings
from app.db import create_pool

log = logging.getLogger("agentcogs.stripe_sync")
logging.basicConfig(level=logging.INFO)

if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key


async def sync_yesterday():
    pool = await create_pool()
    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        async with pool.acquire() as db:
            rows = await db.fetch(
                """
                SELECT
                    c.stripe_customer_id,
                    w.stripe_account_id,
                    c.id AS customer_id,
                    w.id AS workspace_id,
                    SUM(e.total_usd) AS total,
                    array_agg(e.id) AS event_ids
                FROM cost_events e
                JOIN customers c ON c.id = e.customer_id
                JOIN workspaces w ON w.id = c.workspace_id
                WHERE e.stripe_synced_at IS NULL
                  AND c.stripe_customer_id IS NOT NULL
                  AND w.stripe_account_id IS NOT NULL
                  AND e.ts::date = $1
                  AND e.status = 'completed'
                GROUP BY c.stripe_customer_id, w.stripe_account_id, c.id, w.id
                """,
                yesterday,
            )

            log.info("syncing %d customer-days to stripe for %s", len(rows), yesterday)

            for r in rows:
                identifier = (
                    f"acg_{r['workspace_id']}_{r['customer_id']}_{yesterday.isoformat()}"
                )
                value_cents = int(float(r["total"]) * 100)
                if value_cents <= 0:
                    continue

                try:
                    stripe.billing.MeterEvent.create(
                        event_name=settings.stripe_meter_event_name,
                        payload={
                            "stripe_customer_id": r["stripe_customer_id"],
                            "value": str(value_cents),
                        },
                        identifier=identifier,
                        stripe_account=r["stripe_account_id"],
                    )
                    await db.execute(
                        "UPDATE cost_events SET stripe_synced_at=NOW() WHERE id = ANY($1)",
                        r["event_ids"],
                    )
                    log.info(
                        "synced ws=%s cust=%s cents=%d",
                        r["workspace_id"],
                        r["customer_id"],
                        value_cents,
                    )

                except stripe.error.IdempotencyError:
                    await db.execute(
                        "UPDATE cost_events SET stripe_synced_at=NOW() WHERE id = ANY($1)",
                        r["event_ids"],
                    )
                    log.info(
                        "idempotent skip ws=%s cust=%s",
                        r["workspace_id"],
                        r["customer_id"],
                    )

                except Exception as e:
                    log.exception(
                        "sync failed ws=%s cust=%s: %s",
                        r["workspace_id"],
                        r["customer_id"],
                        e,
                    )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(sync_yesterday())
