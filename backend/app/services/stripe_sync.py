"""Nightly Stripe Billing Meter sync — batched per customer per day."""
import logging
from datetime import datetime, timedelta, timezone

import stripe

from ..config import settings

log = logging.getLogger("agentcogs.stripe_sync")

if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key


async def sync_daily(db) -> int:
    """Sync yesterday's unsynced events. Returns count of meter events created."""
    if not settings.stripe_api_key:
        log.info("stripe sync skipped — no API key")
        return 0

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()

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
        GROUP BY c.stripe_customer_id, w.stripe_account_id, c.id, w.id
        """,
        yesterday,
    )

    synced = 0
    for r in rows:
        identifier = f"acg_{r['workspace_id']}_{r['customer_id']}_{yesterday.isoformat()}"
        try:
            stripe.billing.MeterEvent.create(
                event_name=settings.stripe_meter_event_name,
                payload={
                    "stripe_customer_id": r["stripe_customer_id"],
                    "value": str(int(float(r["total"]) * 100)),
                },
                identifier=identifier,
                stripe_account=r["stripe_account_id"],
            )
            await db.execute(
                "UPDATE cost_events SET stripe_synced_at=NOW() WHERE id = ANY($1)",
                r["event_ids"],
            )
            synced += 1
        except stripe.error.StripeError as e:
            if getattr(e, "code", None) == "idempotency_error":
                await db.execute(
                    "UPDATE cost_events SET stripe_synced_at=NOW() WHERE id = ANY($1)",
                    r["event_ids"],
                )
                synced += 1
            else:
                log.error("stripe meter event failed: %s", e)

    return synced
