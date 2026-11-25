"""Redis lease. Postgres owns the row. This script owns the in-flight hold."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_LUA = Path(__file__).resolve().parents[1] / "kernel" / "admit.lua"
_TEXT = _LUA.read_text()
RESERVE_LUA, _rest = _TEXT.split("-- SETTLE\n", 1)
SETTLE_LUA, SWEEP_LUA = _rest.split("-- SWEEP\n", 1)


def tag_for(workspace_id: str, customer_id: str) -> str:
    return f"{{ws:{workspace_id}:cust:{customer_id}}}"


def month_key(when: datetime | None = None) -> str:
    moment = when or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m")


def keys_for(workspace_id: str, customer_id: str, month: str, run_id: str | None = None) -> dict[str, str]:
    tag = tag_for(workspace_id, customer_id)
    out = {
        "spent": f"{tag}:spent:{month}",
        "holds": f"{tag}:holds",
        "exp": f"{tag}:exp",
    }
    if run_id is not None:
        out["settled"] = f"{tag}:settled:{run_id}"
    return out


async def reserve(redis, workspace_id: str, customer_id: str, run_id: str, estimate_micro: int, ttl_seconds: int, budget_micro: int | None, month: str | None = None) -> str:
    found = keys_for(workspace_id, customer_id, month or month_key())
    budget = -1 if budget_micro is None else int(budget_micro)
    raw = await redis.eval(
        RESERVE_LUA,
        3,
        found["spent"],
        found["holds"],
        found["exp"],
        run_id,
        int(estimate_micro),
        int(ttl_seconds),
        budget,
    )
    return str(raw[0])


async def settle(redis, workspace_id: str, customer_id: str, run_id: str, actual_micro: int, month: str | None = None) -> int:
    found = keys_for(workspace_id, customer_id, month or month_key(), run_id)
    raw = await redis.eval(
        SETTLE_LUA,
        4,
        found["spent"],
        found["holds"],
        found["exp"],
        found["settled"],
        int(actual_micro),
        run_id,
    )
    return int(raw)


async def sweep_holds(redis, workspace_id: str, customer_id: str) -> int:
    found = keys_for(workspace_id, customer_id, month_key())
    raw = await redis.eval(SWEEP_LUA, 2, found["holds"], found["exp"])
    return int(raw)


async def spent_micro(redis, workspace_id: str, customer_id: str, month: str | None = None) -> int:
    found = keys_for(workspace_id, customer_id, month or month_key())
    raw = await redis.get(found["spent"])
    return int(raw or 0)


async def set_spent(redis, workspace_id: str, customer_id: str, month: str, micro: int) -> None:
    found = keys_for(workspace_id, customer_id, month)
    await redis.set(found["spent"], int(micro))
