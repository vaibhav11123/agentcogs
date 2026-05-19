from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from ..deps import auth_workspace_by_jwt

router = APIRouter()


@router.get("/v1/customers/{customer_id}/events")
async def list_events(
    customer_id: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
    limit: int = 100,
):
    rows = await request.app.state.db.fetch(
        """
        SELECT id, workflow_id, ts, status, total_usd,
               model_breakdown, node_breakdown, error
        FROM cost_events
        WHERE workspace_id=$1 AND customer_id=$2
        ORDER BY ts DESC LIMIT $3
        """,
        ws["id"],
        customer_id,
        limit,
    )
    return [dict(r) for r in rows]


@router.get("/v1/customers/{customer_id}/daily")
async def daily_costs(
    customer_id: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
    days: int = 30,
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await request.app.state.db.fetch(
        """
        SELECT date_trunc('day', ts)::date AS day,
               SUM(total_usd) AS usd,
               COUNT(*) AS runs
        FROM cost_events
        WHERE workspace_id=$1 AND customer_id=$2 AND ts >= $3
        GROUP BY day ORDER BY day
        """,
        ws["id"],
        customer_id,
        since,
    )
    return [
        {"day": r["day"].isoformat(), "usd": float(r["usd"]), "runs": r["runs"]}
        for r in rows
    ]


@router.get("/v1/customers/{customer_id}/nodes")
async def node_breakdown(
    customer_id: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
    days: int = 30,
):
    """Aggregate node_breakdown JSONB across recent runs."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await request.app.state.db.fetch(
        """
        SELECT key AS node, SUM((value)::numeric) AS usd
        FROM cost_events e, jsonb_each_text(e.node_breakdown)
        WHERE e.workspace_id=$1 AND e.customer_id=$2 AND e.ts >= $3
        GROUP BY key ORDER BY usd DESC
        """,
        ws["id"],
        customer_id,
        since,
    )
    return [{"node": r["node"], "usd": float(r["usd"])} for r in rows]
