from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import auth_workspace_by_jwt

router = APIRouter()


@router.get("/v1/events/by-run/{run_id}")
async def event_by_run(
    run_id: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    row = await request.app.state.db.fetchrow(
        """
        SELECT id, customer_id, workflow_id, ts, status, total_usd, error
        FROM cost_events
        WHERE id = $1 AND workspace_id = $2
        """,
        run_id,
        ws["id"],
    )
    if not row:
        raise HTTPException(404, "event not found")
    return dict(row)


@router.get("/v1/onboarding/status")
async def onboarding_status(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    db = request.app.state.db
    row = await db.fetchrow(
        """
        SELECT sdk_first_seen_at, first_cost_event_at
        FROM workspaces WHERE id = $1
        """,
        ws["id"],
    )
    cust_count = await db.fetchval(
        "SELECT COUNT(*) FROM customers WHERE workspace_id = $1",
        ws["id"],
    )
    event_count = await db.fetchval(
        "SELECT COUNT(*) FROM cost_events WHERE workspace_id = $1",
        ws["id"],
    )
    first_event = bool(row and row["first_cost_event_at"])
    return {
        "first_event": first_event,
        "sdk_seen": bool(row and row["sdk_first_seen_at"]),
        "first_event_at": (
            row["first_cost_event_at"].isoformat()
            if row and row["first_cost_event_at"]
            else None
        ),
        "customer_count": int(cust_count or 0),
        "event_count": int(event_count or 0),
        "checklist": {
            "has_customers": int(cust_count or 0) > 0,
            "has_events": int(event_count or 0) > 0,
        },
    }
