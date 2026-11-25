"""Integer micro-USD rounding. No remainder is carried to the next lane."""

from __future__ import annotations

_INT64_MAX = 2**63 - 1


def mul_div_round_half_up(numer: int, denom: int) -> int:
    if denom <= 0:
        raise ValueError("denom")
    if numer < 0:
        raise ValueError("LANE_NEGATIVE")
    if numer > _INT64_MAX:
        raise ValueError("AMOUNT_OVERFLOW")
    quotient, remainder = divmod(numer, denom)
    if remainder * 2 >= denom:
        quotient += 1
    return quotient


def lane_micro(tokens: int, usd_per_million: int, num: int, den: int) -> int:
    if tokens < 0:
        raise ValueError("LANE_NEGATIVE")
    product = tokens * usd_per_million * num
    if product > _INT64_MAX:
        raise ValueError("AMOUNT_OVERFLOW")
    return mul_div_round_half_up(product, den)
