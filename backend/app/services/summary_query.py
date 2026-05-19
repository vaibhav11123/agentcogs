from datetime import datetime, timedelta, timezone

from ..services.leaderboard_query import fetch_leaderboard


async def fetch_summary(db, workspace_id: str) -> dict:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    since = now - timedelta(days=30)

    leaderboard = await fetch_leaderboard(db, workspace_id)

    total_cost = sum(r["cost_usd"] for r in leaderboard)
    total_revenue = sum(r["revenue_usd"] for r in leaderboard)
    blended_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0.0

    over_budget_count = sum(1 for r in leaderboard if r["budget_status"] == "exceeded")
    warn_budget_count = sum(1 for r in leaderboard if r["budget_status"] == "warn")

    anomaly_count = await db.fetchval(
        """
        SELECT COUNT(*) FROM anomalies
        WHERE workspace_id = $1 AND created_at >= $2
        """,
        workspace_id,
        now - timedelta(days=7),
    )

    daily_rows = await db.fetch(
        """
        SELECT date_trunc('day', ts)::date AS day,
               SUM(total_usd) AS cost_usd,
               COUNT(*) AS runs
        FROM cost_events
        WHERE workspace_id = $1 AND ts >= $2
        GROUP BY day ORDER BY day
        """,
        workspace_id,
        since,
    )

    daily_trend = [
        {
            "day": r["day"].isoformat(),
            "cost_usd": round(float(r["cost_usd"]), 4),
            "runs": r["runs"],
        }
        for r in daily_rows
    ]

    return {
        "total_cost_usd": round(total_cost, 2),
        "total_revenue_usd": round(total_revenue, 2),
        "blended_margin_pct": round(blended_margin, 2),
        "over_budget_count": over_budget_count,
        "warn_budget_count": warn_budget_count,
        "anomaly_count_7d": int(anomaly_count or 0),
        "customer_count": len(leaderboard),
        "daily_trend": daily_trend,
        "month_start": month_start.isoformat(),
    }
