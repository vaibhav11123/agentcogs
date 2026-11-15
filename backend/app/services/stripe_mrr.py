"""Monthly recurring revenue from a Stripe subscription object.

Stripe has no MRR field. The figure is the monthly-normalised value of
active, non-metered prices, net of a percent or amount coupon when the
coupon is expanded on the subscription. Metered prices are skipped.
https://docs.stripe.com/api/subscriptions/list
https://www.hitmrr.com/learn/calculate-mrr-from-stripe
"""

_MONTHS = {"day": 12 / 365, "week": 12 / 52, "month": 1.0, "year": 12.0}


def _period_months(interval: str | None, interval_count: int | None) -> float | None:
    per = _MONTHS.get(interval or "")
    count = interval_count or 1
    if per is None or count <= 0:
        return None
    return per * count


def _plain(obj):
    """Stripe resources are not dicts. .get() raises AttributeError on them."""
    if obj is None or isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return obj


def subscription_monthly_usd(sub: dict) -> float:
    sub = _plain(sub) or {}
    gross = 0.0
    period = 1.0
    items = (sub.get("items") or {}).get("data") or []
    for item in items:
        price = item.get("price") or {}
        recurring = price.get("recurring") or {}
        unit = price.get("unit_amount")
        if unit is None or price.get("recurring") is None:
            continue
        if recurring.get("usage_type") == "metered":
            continue
        months = _period_months(recurring.get("interval"), recurring.get("interval_count"))
        if not months:
            continue
        quantity = item.get("quantity") or 1
        gross += (unit * quantity) / 100 / months
        period = months

    net = gross
    coupons = []
    if isinstance(sub.get("discount"), dict):
        coupons.append((sub["discount"].get("coupon") or {}))
    for discount in sub.get("discounts") or []:
        if isinstance(discount, dict):
            coupons.append(discount.get("coupon") or {})
    for coupon in coupons:
        if not isinstance(coupon, dict) or coupon.get("valid") is False:
            continue
        percent = coupon.get("percent_off") or 0
        if percent:
            net *= 1 - percent / 100
        amount = coupon.get("amount_off") or 0
        if amount and period:
            net -= (amount / 100) / period
    return round(max(0.0, net), 2)
