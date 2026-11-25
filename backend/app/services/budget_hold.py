"""Hold back one typical run before a budget check says the customer is still fine.

Two runs already in flight can both read the same remaining balance and both
pass. The hold is the median of the recent runs, and the check treats that
amount as already spoken for. Fewer than three runs means there is no typical
run yet, so the hold is zero and the check is spent against the cap.

Spent, hold, and budget are decimals. The warn line is four fifths of the
budget, compared without binary floats.
"""

from decimal import Decimal

from .money import as_usd, hold_usd


def next_run_hold(costs: list) -> Decimal:
    recent = [amount for amount in (as_usd(c) for c in costs) if amount > 0][:20]
    if len(recent) < 3:
        return Decimal("0")
    ordered = sorted(recent)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[mid]
    else:
        median = (ordered[mid - 1] + ordered[mid]) / Decimal(2)
    return hold_usd(median)


def budget_decision(spent, budget, hold) -> str:
    if budget is None:
        return "ok"
    spent_d = as_usd(spent)
    budget_d = as_usd(budget)
    hold_d = as_usd(hold)
    if hold_d < 0:
        hold_d = Decimal("0")
    if spent_d + hold_d >= budget_d:
        return "exceeded"
    if spent_d * 5 >= budget_d * 4:
        return "warn"
    return "ok"
