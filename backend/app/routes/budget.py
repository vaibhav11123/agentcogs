import logging
import time
from datetime import datetime, timezone

import redis as redis_lib
from fastapi import APIRouter, Depends, Request

from ..deps import auth_workspace_by_api_key
from ..models import BudgetResponse
from ..services.admission import RESERVE_LUA, keys_for, month_key
from ..services.budget_hold import budget_decision, next_run_hold
from .ingest import usd_to_micro

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

    hold = await _next_run_hold(db, cust_id)
    status = budget_decision(spent, budget_usd, hold)
    enforce = await _enforce_flag(db, ws_id)
    decision, spent_micro, held_micro = await _reserve_view(
        redis_client, ws_id, cust_id, hold, budget_usd
    )
    if not enforce and decision in {"exceeded", "busy"}:
        try:
            await db.execute(
                """
                INSERT INTO budget_audit
                  (workspace_id, customer_id, legacy_status, reserve_decision,
                   spent_micro, held_micro, estimate_micro, budget_micro)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                ws_id,
                cust_id,
                status,
                decision,
                spent_micro,
                held_micro,
                usd_to_micro(hold),
                None if budget_usd is None else usd_to_micro(budget_usd),
            )
        except Exception:
            log.exception("budget audit insert failed")
    return BudgetResponse(
        status=status,
        spent_usd=spent,
        budget_usd=budget_usd,
        remaining_usd=max(0.0, budget_usd - spent),
        source=source,
        hold_usd=hold,
        decision=decision,
        enforce=enforce,
    )


async def _enforce_flag(db, ws_id) -> bool:
    try:
        flag = await db.fetchval("SELECT budget_enforce FROM workspaces WHERE id = $1", ws_id)
    except Exception:
        return False
    return flag if isinstance(flag, bool) else False


async def _reserve_view(redis_client, ws_id, cust_id, hold: float, budget_usd: float | None):
    estimate = usd_to_micro(hold)
    budget = -1 if budget_usd is None else usd_to_micro(budget_usd)
    try:
        found = keys_for(str(ws_id), str(cust_id), month_key())
        raw = await redis_client.eval(
            RESERVE_LUA,
            3,
            found["spent"],
            found["holds"],
            found["exp"],
            "preflight",
            estimate,
            300,
            budget,
        )
        return str(raw[0]), int(raw[1]), int(raw[2])
    except Exception:
        log.exception("reserve failed")
        return "ok", 0, 0


async def _next_run_hold(db, cust_id: str) -> float:
    try:
        rows = await db.fetch(
            """
            SELECT total_usd FROM cost_events
            WHERE customer_id = $1
            ORDER BY ts DESC
            LIMIT 20
            """,
            cust_id,
        )
    except Exception:
        return 0.0
    if not isinstance(rows, list):
        return 0.0
    return next_run_hold([float(r["total_usd"]) for r in rows])
