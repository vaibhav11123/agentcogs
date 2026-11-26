"""Dollars on the wire, in micro-USD.

One micro-USD is 0.000001 dollar. The budget counter stores that integer.
Responses write the same unit as a JSON number with at most six decimal
places, so a client does not see binary float tails.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

QUANT = Decimal("0.000001")
_HOLD = Decimal("0.0001")
_MICRO = Decimal(1_000_000)


def as_usd(value) -> Decimal:
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, bool):
        raise TypeError("usd value must be a number")
    elif isinstance(value, int):
        dec = Decimal(value)
    else:
        dec = Decimal(str(value))
    return dec.quantize(QUANT, rounding=ROUND_HALF_UP)


def micro_to_usd(micro: int) -> Decimal:
    return (Decimal(int(micro)) / _MICRO).quantize(QUANT, rounding=ROUND_HALF_UP)


def usd_to_micro(value) -> int:
    return int(as_usd(value) * _MICRO)


def dollars_remaining(budget: Decimal | None, spent: Decimal) -> Decimal | None:
    if budget is None:
        return None
    gap = budget - spent
    if gap < 0:
        return Decimal("0")
    return gap.quantize(QUANT, rounding=ROUND_HALF_UP)


def hold_usd(value: Decimal) -> Decimal:
    return value.quantize(_HOLD, rounding=ROUND_HALF_EVEN)


def dumps_usd(payload: dict) -> bytes:
    return _encode(payload).encode()


def _encode(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        text = format(value.quantize(QUANT, rounding=ROUND_HALF_UP), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in {"", "-0"}:
            text = "0"
        return text
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            return "null"
        return _encode(as_usd(value))
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, dict):
        parts = [json.dumps(str(key)) + ":" + _encode(item) for key, item in value.items()]
        return "{" + ",".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    raise TypeError(f"cannot encode {type(value).__name__}")
