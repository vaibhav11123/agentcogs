"""Month-pace for a cost that accrues daily against a monthly revenue figure.

Cost is projected with a straight daily rate. Revenue is left as the full
monthly amount, because a subscription fee does not arrive in thirtieths.
The projection is withheld until the third day so one early spike is not
multiplied across the month. GrowPanel uses the same linear form and waits
before drawing it: https://growpanel.io/docs/understanding-your-data/projections/
"""

import calendar
from datetime import datetime

MIN_ELAPSED_DAYS = 3


def project_month(
    cost_usd: float, revenue_usd: float, now: datetime
) -> tuple[float | None, float | None]:
    elapsed = now.day
    if elapsed < MIN_ELAPSED_DAYS or cost_usd < 0:
        return None, None
    days = calendar.monthrange(now.year, now.month)[1]
    projected_cost = cost_usd * days / elapsed
    if revenue_usd <= 0:
        return round(projected_cost, 2), None
    margin = (revenue_usd - projected_cost) / revenue_usd * 100
    return round(projected_cost, 2), round(margin, 2)
