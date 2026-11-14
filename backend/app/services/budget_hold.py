"""Hold back one typical run before a budget check says the customer is still fine.

Two runs already in flight can both read the same remaining balance and both
pass. The hold is the median of the recent runs, and the check treats that
amount as already spoken for. Fewer than three runs means there is no typical
run yet, so the hold is zero and the check is spent against the cap.
"""


def next_run_hold(costs: list[float]) -> float:
    recent = [c for c in costs if c > 0][:20]
    if len(recent) < 3:
        return 0.0
    ordered = sorted(recent)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[mid]
    else:
        median = (ordered[mid - 1] + ordered[mid]) / 2
    return round(median, 4)


def budget_decision(spent: float, budget: float | None, hold: float) -> str:
    if budget is None:
        return "ok"
    if spent + max(hold, 0.0) >= budget:
        return "exceeded"
    if spent >= 0.8 * budget:
        return "warn"
    return "ok"
