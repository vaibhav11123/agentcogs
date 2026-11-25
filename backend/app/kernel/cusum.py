"""Tabular CUSUM on the log of daily allocated micro-USD.

The first 30 positive days are the reference. They do not move S and they
cannot signal. A flat reference has sigma 0, and the residual is used as z.
"""

from __future__ import annotations

import math


def page_kinds(zscore: bool, cusum: bool) -> list[str]:
    kinds: list[str] = []
    if zscore:
        kinds.append("zscore")
    if cusum:
        kinds.append("cusum")
    return kinds


def cusum_signals(days: list[tuple[int, int]]) -> bool:
    positive = [(int(weekday), int(micro)) for weekday, micro in days if int(micro) > 0]
    if len(positive) <= 30:
        return False
    reference = positive[:30]
    buckets: dict[int, list[float]] = {}
    for weekday, micro in reference:
        buckets.setdefault(weekday, []).append(math.log(micro))
    baseline = {weekday: sum(values) / len(values) for weekday, values in buckets.items()}
    residuals = [math.log(micro) - baseline[weekday] for weekday, micro in reference]
    mean = sum(residuals) / 30
    variance = sum((item - mean) ** 2 for item in residuals) / 30
    sigma = math.sqrt(variance)
    statistic = 0.0
    signaled = False
    for weekday, micro in positive[30:]:
        if weekday not in baseline:
            continue
        residual = math.log(micro) - baseline[weekday]
        score = residual if sigma == 0 else residual / sigma
        statistic = max(0.0, statistic + score - 0.5)
        if statistic > 5:
            signaled = True
    return signaled
