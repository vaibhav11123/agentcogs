"""Rolling z-score anomaly detection.

- Need ≥5 historical points or stddev is meaningless
- Flag if z > 2.5 OR current > 3× mean
- Below 5 samples: hard threshold $5 per run
- 6-hour suppression per (customer, workflow) to prevent storms
"""
import logging
from .alerts import send_alert

log = logging.getLogger("agentcogs.anomaly")

HARD_THRESHOLD_USD = 5.00
Z_THRESHOLD = 2.5
MULT_THRESHOLD = 3.0
SUPPRESSION_HOURS = 6


async def check_anomaly(
    db,
    redis,
    *,
    workspace_id: str,
    cost_event_id: str,
    customer_id: str,
    workflow_id: str,
    current_usd: float,
):
    try:
        stats = await db.fetchrow(
            """
            SELECT AVG(total_usd) AS mean,
                   STDDEV(total_usd) AS stddev,
                   COUNT(*) AS n
            FROM cost_events
            WHERE customer_id = $1 AND workflow_id = $2
              AND ts > NOW() - INTERVAL '30 days'
              AND id != $3
              AND status = 'completed'
            """,
            customer_id,
            workflow_id,
            cost_event_id,
        )

        n = stats["n"]
        flagged = False
        z = mult = mean = None

        if n < 5:
            if current_usd > HARD_THRESHOLD_USD:
                flagged = True
                mult = current_usd / 0.50
        else:
            mean = float(stats["mean"])
            stddev = max(float(stats["stddev"] or 0), 0.0001)
            z = (current_usd - mean) / stddev
            mult = current_usd / mean if mean > 0 else 0
            if z > Z_THRESHOLD or mult > MULT_THRESHOLD:
                flagged = True

        if not flagged:
            return

        suppressed = await db.fetchval(
            """
            SELECT 1 FROM alert_suppressions
            WHERE workspace_id=$1 AND customer_id=$2 AND workflow_id=$3
              AND suppress_until > NOW()
            """,
            workspace_id,
            customer_id,
            workflow_id,
        )
        if suppressed:
            log.info(
                "anomaly suppressed ws=%s cust=%s wf=%s",
                workspace_id,
                customer_id,
                workflow_id,
            )
            return

        anomaly_id = await db.fetchval(
            """
            INSERT INTO anomalies
              (workspace_id, cost_event_id, customer_id, z_score, multiplier, mean_usd)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
            """,
            workspace_id,
            cost_event_id,
            customer_id,
            z,
            mult,
            mean,
        )

        await db.execute(
            """
            INSERT INTO alert_suppressions
              (workspace_id, customer_id, workflow_id, suppress_until)
            VALUES ($1,$2,$3, NOW() + INTERVAL '6 hours')
            ON CONFLICT (workspace_id, customer_id, workflow_id)
            DO UPDATE SET suppress_until = EXCLUDED.suppress_until
            """,
            workspace_id,
            customer_id,
            workflow_id,
        )

        await send_alert(db, anomaly_id)
        log.info("anomaly fired id=%s ws=%s mult=%.2f", anomaly_id, workspace_id, mult or 0)

    except Exception as e:
        log.exception("anomaly check failed: %s", e)
