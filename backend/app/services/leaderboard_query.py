from datetime import datetime, timezone


async def fetch_leaderboard(db, workspace_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = await db.fetch(
        """
        SELECT
            c.id, c.external_id, c.display_name,
            c.monthly_budget_usd,
            c.monthly_revenue_usd,
            COALESCE(stats.runs, 0)  AS runs,
            COALESCE(stats.cost, 0)  AS cost_usd
        FROM customers c
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS runs, SUM(total_usd) AS cost
            FROM cost_events e
            WHERE e.customer_id = c.id AND e.ts >= $2
        ) stats ON true
        WHERE c.workspace_id = $1
        ORDER BY cost_usd DESC NULLS LAST
        """,
        workspace_id,
        month_start,
    )

    out = []
    for r in rows:
        cost = float(r["cost_usd"])
        rev = float(r["monthly_revenue_usd"] or 0)
        budget = float(r["monthly_budget_usd"]) if r["monthly_budget_usd"] else None

        margin = ((rev - cost) / rev * 100) if rev > 0 else 0.0
        if budget is None:
            status = "ok"
        elif cost >= budget:
            status = "exceeded"
        elif cost >= 0.8 * budget:
            status = "warn"
        else:
            status = "ok"

        out.append({
            "customer_id": str(r["id"]),
            "external_id": r["external_id"],
            "display_name": r["display_name"] or r["external_id"],
            "runs": r["runs"],
            "cost_usd": cost,
            "revenue_usd": rev,
            "margin_pct": round(margin, 2),
            "budget_usd": budget,
            "budget_status": status,
        })
    return out
