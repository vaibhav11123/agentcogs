import logging
import time
from decimal import Decimal

import redis as redis_lib
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from ..deps import auth_workspace_by_api_key
from ..models import BudgetResponse
from ..services.admission import RESERVE_LUA, keys_for, month_key
from ..services.budget_hold import budget_decision, next_run_hold
from ..services.money import as_usd, dollars_remaining, dumps_usd, micro_to_usd
from .ingest import usd_to_micro

router = APIRouter()
log = logging.getLogger("agentcogs.budget")

_pg_cache: dict[tuple, tuple[Decimal, float]] = {}
_warn_last: float = 0.0


def _cache_get(ws_id: str, cust_id: str) -> Decimal | None:
    key = (ws_id, cust_id)
    entry = _pg_cache.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.monotonic() - ts > 60:
        _pg_cache.pop(key, None)
        return None
    return value


def _cache_set(ws_id: str, cust_id: str, value: Decimal) -> None:
    _pg_cache[(ws_id, cust_id)] = (value, time.monotonic())


def _warn_fallback_once() -> None:
    global _warn_last
    now = time.monotonic()
    if now - _warn_last >= 60:
        _warn_last = now
        log.warning("Redis unavailable for budget spend — using Postgres fallback")


async def _spent_from_postgres(db, ws_id: str, cust_id: str) -> Decimal:
    cached = _cache_get(ws_id, cust_id)
    if cached is not None:
        return cached
    spent = await db.fetchval(
        """
        SELECT COALESCE(SUM(micro), 0)::bigint FROM (
            SELECT actual_micro AS micro
            FROM settlement_receipts
            WHERE workspace_id = $1 AND customer_id = $2
              AND month = date_trunc('month', NOW())::date
            UNION ALL
            SELECT f.incurred_micro
            FROM ledger_facts f
            WHERE f.workspace_id = $1 AND f.customer_id = $2
              AND f.event_time >= date_trunc('month', NOW())
              AND f.event_time < date_trunc('month', NOW()) + INTERVAL '1 month'
              AND NOT EXISTS (
                  SELECT 1 FROM settlement_receipts r
                  WHERE r.workspace_id = f.workspace_id AND r.run_id = f.run_id
              )
            UNION ALL
            SELECT (e.total_usd * 1000000)::bigint
            FROM cost_events e
            WHERE e.workspace_id = $1 AND e.customer_id = $2
              AND e.ts >= date_trunc('month', NOW())
              AND e.ts < date_trunc('month', NOW()) + INTERVAL '1 month'
              AND NOT EXISTS (
                  SELECT 1 FROM settlement_receipts r
                  WHERE r.workspace_id = e.workspace_id AND r.run_id = e.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM ledger_facts f
                  WHERE f.workspace_id = e.workspace_id AND f.run_id = e.id
              )
        ) committed
        """,
        ws_id,
        cust_id,
    )
    value = micro_to_usd(int(spent or 0))
    _cache_set(ws_id, cust_id, value)
    return value


def _budget_response(**fields) -> Response:
    BudgetResponse(**{
        key: (float(value) if isinstance(value, Decimal) else value)
        for key, value in fields.items()
    })
    return Response(content=dumps_usd(fields), media_type="application/json")


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
    redis_failed = False
    try:
        cached = await redis_client.get(cache_key)
    except (redis_lib.exceptions.RedisError, OSError):
        cached = None
        redis_failed = True
    if cached:
        parts = cached.split("|")
        cust_id = parts[0]
        budget_usd = None if parts[1] == "None" else as_usd(parts[1])
    else:
        row = await db.fetchrow(
            "SELECT id, monthly_budget_usd FROM customers "
            "WHERE workspace_id=$1 AND external_id=$2",
            ws_id,
            customer,
        )
        if not row:
            return _budget_response(
                status="ok",
                spent_usd=Decimal("0"),
                budget_usd=None,
                remaining_usd=None,
                source="postgres_fallback" if redis_failed else source,
            )
        cust_id = str(row["id"])
        raw_budget = row["monthly_budget_usd"]
        budget_usd = as_usd(raw_budget) if raw_budget else None
        if not redis_failed:
            try:
                await redis_client.setex(
                    cache_key, 300, f"{cust_id}|{budget_usd if budget_usd is not None else 'None'}"
                )
            except (redis_lib.exceptions.RedisError, OSError):
                redis_failed = True

    if redis_failed:
        _warn_fallback_once()
        source = "postgres_fallback"
        spent = await _spent_from_postgres(db, ws_id, cust_id)
    else:
        try:
            found = keys_for(str(ws_id), str(cust_id), month_key())
            spent_raw = await redis_client.get(found["spent"])
        except (redis_lib.exceptions.RedisError, OSError):
            spent_raw = None
            redis_failed = True
        if redis_failed or spent_raw is None:
            if redis_failed:
                _warn_fallback_once()
            source = "postgres_fallback"
            spent = await _spent_from_postgres(db, ws_id, cust_id)
        else:
            spent = micro_to_usd(int(spent_raw))

    if budget_usd is None:
        return _budget_response(
            status="ok",
            spent_usd=spent,
            budget_usd=None,
            remaining_usd=None,
            source=source,
        )

    hold = await _next_run_hold(db, cust_id)
    status = budget_decision(spent, budget_usd, hold)
    enforce = await _enforce_flag(db, ws_id)
    if redis_failed:
        decision = status
        spent_micro = usd_to_micro(spent)
        held_micro = usd_to_micro(hold)
    else:
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
    return _budget_response(
        status=status,
        spent_usd=spent,
        budget_usd=budget_usd,
        remaining_usd=dollars_remaining(budget_usd, spent),
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


async def _reserve_view(redis_client, ws_id, cust_id, hold: Decimal, budget_usd: Decimal | None):
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


async def _next_run_hold(db, cust_id: str) -> Decimal:
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
        return Decimal("0")
    if not isinstance(rows, list):
        return Decimal("0")
    return next_run_hold([r["total_usd"] for r in rows])
