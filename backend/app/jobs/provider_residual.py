"""Provider bill versus the ledger. The difference is not given to a customer."""

from __future__ import annotations

from datetime import date, timedelta


def record_residual(ledger_micro: int, provider_micro: int | None) -> int | None:
    if provider_micro is None:
        return None
    return int(provider_micro) - int(ledger_micro)


def day_is_closed(event_date: date, today: date) -> bool:
    return event_date <= today - timedelta(days=2)


def record_drift(ledger_micro: int, redis_micro: int) -> dict:
    return {
        "ledger_micro": int(ledger_micro),
        "redis_micro": int(redis_micro),
        "difference_micro": int(redis_micro) - int(ledger_micro),
    }


async def write_residual(db, workspace_id, provider: str, event_date: date, ledger_micro: int, provider_fetch, today: date) -> int | None:
    if not day_is_closed(event_date, today):
        return None
    provider_micro = await provider_fetch()
    residual = record_residual(ledger_micro, provider_micro)
    await db.execute(
        """
        INSERT INTO ledger_residuals
          (workspace_id, provider, event_date, ledger_micro, provider_micro, residual_micro)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        workspace_id,
        provider,
        event_date,
        ledger_micro,
        provider_micro,
        residual,
    )
    return residual
