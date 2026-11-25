"""Formulas for the local financial report. No model call and no network."""

from __future__ import annotations

from datetime import date, timedelta


def money_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def plan_margin(revenue_micro: int | None, ai_micro: int) -> float | None:
    """Revenue minus attributable AI cost, over revenue. Missing revenue stays blank."""
    if revenue_micro is None:
        return None
    return money_ratio(revenue_micro - ai_micro, revenue_micro)


def recommended_budget_micro(price_micro: int, target_percent: int) -> int:
    if price_micro < 0 or not 0 <= target_percent <= 100:
        raise ValueError("BUDGET_INPUT")
    return price_micro * (100 - target_percent) // 100


def warning_micro(budget_micro: int) -> int:
    if budget_micro < 0:
        raise ValueError("BUDGET_INPUT")
    return budget_micro * 80 // 100


def concentration(customer_micros: dict[str, int], top_n: int = 5) -> dict | None:
    """Share of allocated micros held by the top customers. Hidden on a short book."""
    if top_n < 1 or len(customer_micros) <= top_n:
        return None
    total = sum(customer_micros.values())
    if total <= 0:
        return None
    ordered = sorted(customer_micros.items(), key=lambda item: (-item[1], item[0]))
    chosen = ordered[:top_n]
    held = sum(amount for _, amount in chosen)
    return {
        "customers": [name for name, _ in chosen],
        "share": held / total,
        "held_micro": held,
        "total_micro": total,
    }


def unattributed_share(rows: list[dict], today: date) -> float | None:
    """Provider residual over provider micros, for days that ended at least two UTC days ago."""
    cutoff = today - timedelta(days=2)
    closed = []
    for row in rows:
        day = date.fromisoformat(row["day"])
        if day <= cutoff:
            closed.append(row)
    if not closed:
        return None
    provider = sum(int(row["provider_micro"]) for row in closed)
    ledger = sum(int(row["ledger_micro"]) for row in closed)
    if provider <= 0:
        return None
    return (provider - ledger) / provider


def regression_comment(
    previous_exec_micro: int,
    proposed_exec_micro: int,
    previous_month_micro: int,
    driver: str | None = None,
) -> str:
    """Comment body for a controlled before/after. Default is a comment, not a failing check."""
    if previous_exec_micro <= 0 or proposed_exec_micro < 0 or previous_month_micro < 0:
        raise ValueError("PREVIOUS_COST")
    tenths = (proposed_exec_micro - previous_exec_micro) * 1000 // previous_exec_micro
    proposed_month = previous_month_micro * proposed_exec_micro // previous_exec_micro
    lines = [
        "AgentCOGS — Cost regression",
        f"Cost per execution: ${previous_exec_micro / 1_000_000:.3f} -> ${proposed_exec_micro / 1_000_000:.3f}",
        f"Projected monthly cost: ${previous_month_micro / 1_000_000:.0f} -> ${proposed_month / 1_000_000:.0f}",
        f"Cost increase: {tenths // 10}.{tenths % 10}%",
        "Measured using a controlled test workload.",
        "This result is a comment. Failing the check is off until the repository turns it on.",
    ]
    if driver:
        lines.insert(4, f"Likely contributor: {driver}")
    return "\n".join(lines)


def credit_balance(allowance: int, categories: dict[str, int]) -> dict:
    if allowance < 0 or any(amount < 0 for amount in categories.values()):
        raise ValueError("CREDIT_NEGATIVE")
    used = sum(categories.values())
    return {
        "allowance": allowance,
        "used": used,
        "remaining": allowance - used,
        "categories": dict(categories),
    }


def margin_story(months: list[dict]) -> dict | None:
    """Two stored months. Contributors are additional cost, and they are not the whole move."""
    if len(months) < 2:
        return None
    ordered = sorted(months, key=lambda row: row["month"])
    previous, latest = ordered[-2], ordered[-1]
    before = plan_margin(int(previous["revenue_micro"]), int(previous["ai_micro"]))
    after = plan_margin(int(latest["revenue_micro"]), int(latest["ai_micro"]))
    if before is None or after is None:
        return None
    delta = int(latest["ai_micro"]) - int(previous["ai_micro"])
    contributors = {
        "retries": int(latest.get("retry_micro") or 0),
        "pro_usage": int(latest.get("pro_usage_micro") or 0),
        "model_changes": int(latest.get("model_change_micro") or 0),
    }
    named = sum(contributors.values())
    if delta <= 0 or named <= 0 or named >= delta:
        scope = "named"
    else:
        scope = "most"
    return {
        "before": before,
        "after": after,
        "delta_micro": delta,
        "contributors": contributors,
        "scope": scope,
    }
