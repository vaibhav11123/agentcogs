"""Record provider usage inside run() and price it with the shipped book.

Shekel keeps prompt and completion totals. The chat-completions response also
carries cache reads and cache writes. Those lanes are what the server prices.
"""

from __future__ import annotations

import logging
import threading
from contextvars import ContextVar
from decimal import Decimal
from typing import Any

from ._shekel_compat import lanes_from_usage
from .kernel.attribute import price_call
from .localstore import price_book

log = logging.getLogger("agentcogs")

_bucket: ContextVar[list | None] = ContextVar("agentcogs_provider_calls", default=None)
_lock = threading.Lock()
_depth = 0
_saved: dict[str, Any] = {}

_INPUT_LANES = (
    "uncached_input",
    "cache_read",
    "cache_write_5m",
    "cache_write_1h",
    "cache_write_30m",
    "cache_write_12h",
)


def push() -> Any:
    _install()
    box: list = []
    return _bucket.set(box)


def pop(token: Any) -> None:
    _bucket.reset(token)
    _remove()


def snapshot() -> list[dict]:
    box = _bucket.get()
    if not box:
        return []
    return list(box)


def micro_as_usd(micro: int) -> float:
    """Six-decimal dollars. The server parses this back to the same micros."""
    text = format(Decimal(int(micro)) / Decimal(1_000_000), "f")
    return float(text)


def priced_calls(records: list[dict]) -> dict | None:
    """Return ingest fields for these provider responses, or None when empty."""
    if not records:
        return None
    book = price_book()
    calls = []
    by_model: dict[str, dict] = {}
    total = 0
    try:
        for index, record in enumerate(records):
            lanes = lanes_from_usage(record["provider"], record["usage"])
            _priced, micro = price_call(lanes, book)
            model = record.get("model") or "unknown"
            call = {"call_id": f"c{index}", "model": model, "lanes": lanes}
            if record["provider"] == "openai":
                usage = record["usage"]
                if "input_tokens" in usage and usage.get("input_tokens") is not None:
                    call["provider_input_tokens"] = int(usage.get("input_tokens") or 0)
                elif "prompt_tokens" in usage:
                    call["provider_input_tokens"] = int(usage.get("prompt_tokens") or 0)
            calls.append(call)
            total += micro
            row = by_model.setdefault(
                model, {"input_tokens": 0, "output_tokens": 0, "usd": 0.0, "_micro": 0}
            )
            row["input_tokens"] += sum(int(lanes.get(name, 0)) for name in _INPUT_LANES)
            row["output_tokens"] += int(lanes.get("output", 0))
            row["_micro"] += micro
    except ValueError as exc:
        log.warning("provider usage was not priced (%s)", exc)
        return None
    models = {
        model: {
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "usd": micro_as_usd(row["_micro"]),
        }
        for model, row in by_model.items()
    }
    return {
        "calls": calls,
        "book_id": book["book_id"],
        "total_usd": micro_as_usd(total),
        "models": models,
        "total_micro": total,
    }


def _remember(provider: str, model: str | None, usage: Any) -> None:
    box = _bucket.get()
    if box is None or usage is None:
        return
    if hasattr(usage, "model_dump"):
        payload = usage.model_dump()
    elif isinstance(usage, dict):
        payload = dict(usage)
    else:
        return
    box.append({"provider": provider, "model": model, "usage": payload})


def _install() -> None:
    global _depth
    with _lock:
        _depth += 1
        if _depth == 1:
            _wrap()


def _remove() -> None:
    global _depth
    with _lock:
        _depth -= 1
        if _depth == 0:
            _unwrap()


def _wrap() -> None:
    try:
        import openai.resources.chat.completions as oai

        _saved["openai"] = oai.Completions.create
        oai.Completions.create = _openai_create  # type: ignore[method-assign]
    except ImportError:
        pass
    try:
        import anthropic.resources.messages as ant

        _saved["anthropic"] = ant.Messages.create
        ant.Messages.create = _anthropic_create  # type: ignore[method-assign]
    except ImportError:
        pass


def _unwrap() -> None:
    if "openai" in _saved:
        import openai.resources.chat.completions as oai

        oai.Completions.create = _saved.pop("openai")
    if "anthropic" in _saved:
        import anthropic.resources.messages as ant

        ant.Messages.create = _saved.pop("anthropic")


def _openai_create(self: Any, *args: Any, **kwargs: Any) -> Any:
    original = _saved.get("openai")
    response = original(self, *args, **kwargs)
    if kwargs.get("stream") is True:
        return _openai_stream(response)
    _remember("openai", getattr(response, "model", None), getattr(response, "usage", None))
    return response


def _openai_stream(stream: Any):
    last = None
    model = None
    for chunk in stream:
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            last = usage
            model = getattr(chunk, "model", None) or model
        yield chunk
    if last is not None:
        _remember("openai", model, last)


def _anthropic_create(self: Any, *args: Any, **kwargs: Any) -> Any:
    original = _saved.get("anthropic")
    response = original(self, *args, **kwargs)
    if kwargs.get("stream") is True:
        return _anthropic_stream(response)
    _remember("anthropic", getattr(response, "model", None), getattr(response, "usage", None))
    return response


def _anthropic_stream(stream: Any):
    merged: dict = {}
    model = None
    for event in stream:
        kind = getattr(event, "type", None)
        if kind == "message_start":
            message = getattr(event, "message", None)
            model = getattr(message, "model", None) or model
            usage = getattr(message, "usage", None)
            if usage is not None and hasattr(usage, "model_dump"):
                merged.update(usage.model_dump())
        elif kind == "message_delta":
            usage = getattr(event, "usage", None)
            if usage is not None and hasattr(usage, "model_dump"):
                merged.update(usage.model_dump())
        yield event
    if merged:
        _remember("anthropic", model, merged)
