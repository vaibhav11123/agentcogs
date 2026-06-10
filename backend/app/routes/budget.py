import logging
import time
from datetime import datetime, timezone

import redis as redis_lib
from fastapi import APIRouter, Depends, Request

from ..deps import auth_workspace_by_api_key
from ..models import BudgetResponse

router = APIRouter()
log = logging.getLogger("agentcogs.budget")

_pg_cache: dict[tuple, tuple[float, float]] = {}
_warn_last: float = 0.0


def _cache_get(ws_id: str, cust_id: str) -> float | None:
    key = (ws_id, cust_id)
    entry = _pg_cache.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.monotonic() - ts > 60:
        _pg_cache.pop(key, None)
        return None
    return value


def _cache_set(ws_id: str, cust_id: str, value: float) -> None:
    _pg_cache[(ws_id, cust_id)] = (value, time.monotonic())


def _warn_fallback_once() -> None:
    global _warn_last
    now = time.monotonic()
    if now - _warn_last >= 60:
        _warn_last = now
        log.warning("Redis unavailable for budget spend — using Postgres fallback")


async def _spent_from_postgres(db, ws_id: str, cust_id: str) -> float:
    cached = _cache_get(ws_id, cust_id)
    if cached is not None:
        return cached
    spent = await db.fetchval(
        """
        SELECT COALESCE(SUM(total_usd), 0)
        FROM cost_events
        WHERE workspace_id = $1 AND customer_id = $2
          AND ts >= date_trunc('month', NOW())
        """,
        ws_id,
        cust_id,
    )
    value = float(spent or 0)
    _cache_set(ws_id, cust_id, value)
    return value


@router.get("/v1/budget", response_model=BudgetResponse)
async def get_budget(
    workspace: str,  # may be a UUID string or our own ws id
    customer: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_api_key),
):
    db = request.app.state.db
    redis_client = request.app.state.redis
    ws_id = ws["id"]
    source = "redis"

    cache_key = f"cust:{ws_id}:{customer}"
    cached = await redis_client.get(cache_key)
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
            return BudgetResponse(
                status="ok",
                spent_usd=0,
                budget_usd=None,
                remaining_usd=float("inf"),
                source=source,
            )
        cust_id = str(row["id"])
        budget_usd = float(row["monthly_budget_usd"]) if row["monthly_budget_usd"] else None
        await redis_client.setex(cache_key, 300, f"{cust_id}|{budget_usd}")

    try:
        spent_raw = await redis_client.hget(
            f"spend:ws_{ws_id}:cust_{cust_id}:{datetime.now(timezone.utc).strftime('%Y-%m')}",
            "usd",
        )
        spent = float(spent_raw or 0)
    except (redis_lib.exceptions.RedisError, OSError):
        _warn_fallback_once()
        source = "postgres_fallback"
        spent = await _spent_from_postgres(db, ws_id, cust_id)

    if budget_usd is None:
        return BudgetResponse(
            status="ok",
            spent_usd=spent,
            budget_usd=None,
            remaining_usd=float("inf"),
            source=source,
        )

    remaining = budget_usd - spent
    status = "exceeded" if remaining <= 0 else "ok"
    return BudgetResponse(
        status=status,
        spent_usd=spent,
        budget_usd=budget_usd,
        remaining_usd=max(0.0, remaining),
        source=source,
    )
