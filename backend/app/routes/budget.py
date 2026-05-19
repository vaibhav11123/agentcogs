from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from ..deps import auth_workspace_by_api_key
from ..models import BudgetResponse

router = APIRouter()


@router.get("/v1/budget", response_model=BudgetResponse)
async def get_budget(
    workspace: str,  # may be a UUID string or our own ws id
    customer: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_api_key),
):
    db = request.app.state.db
    redis = request.app.state.redis
    ws_id = ws["id"]

    # 5-minute customer cache.
    cache_key = f"cust:{ws_id}:{customer}"
    cached = await redis.get(cache_key)
    if cached:
        parts = cached.split("|")
        cust_id = parts[0]
        budget_usd = float(parts[1]) if parts[1] != "None" else None
    else:
        row = await db.fetchrow(
            "SELECT id, monthly_budget_usd FROM customers "
            "WHERE workspace_id=$1 AND external_id=$2",
            ws_id,
            customer,
        )
        if not row:
            # New customer — no cap yet.
            return BudgetResponse(
                status="ok",
                spent_usd=0,
                budget_usd=None,
                remaining_usd=float("inf"),
            )
        cust_id = str(row["id"])
        budget_usd = float(row["monthly_budget_usd"]) if row["monthly_budget_usd"] else None
        await redis.setex(cache_key, 300, f"{cust_id}|{budget_usd}")

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    spent_raw = await redis.hget(f"spend:ws_{ws_id}:cust_{cust_id}:{month}", "usd")
    spent = float(spent_raw or 0)

    if budget_usd is None:
        return BudgetResponse(
            status="ok",
            spent_usd=spent,
            budget_usd=None,
            remaining_usd=float("inf"),
        )

    remaining = budget_usd - spent
    return BudgetResponse(
        status="exceeded" if remaining <= 0 else "ok",
        spent_usd=spent,
        budget_usd=budget_usd,
        remaining_usd=max(0.0, remaining),
    )
