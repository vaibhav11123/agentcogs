"""Thin adapter over shekel 1.x — single place for version-specific field mapping."""
from __future__ import annotations

from typing import Any, Dict

from shekel import budget as _shekel_budget


def budget(**kwargs: Any):
    """Return shekel budget context manager (signature-stable for agentcogs)."""
    return _shekel_budget(**kwargs)


def normalize_summary(by_model: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert Shekel's by_model summary into a uniform schema.

    Anthropic prompt caching splits input tokens across three fields; all must be summed.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for model, stats in by_model.items():
        model_lower = model.lower()
        if "claude" in model_lower or "anthropic" in model_lower:
            input_total = (
                int(stats.get("input_tokens", 0) or 0)
                + int(stats.get("cache_read_input_tokens", 0) or 0)
                + int(stats.get("cache_creation_input_tokens", 0) or 0)
            )
        else:
            input_total = int(stats.get("input_tokens", 0) or 0)

        out[model] = {
            "input_tokens": input_total,
            "output_tokens": int(stats.get("output_tokens", 0) or 0),
            "usd": float(stats.get("cost", 0) or 0),
        }
    return out


def normalize_summary_data(raw: dict) -> dict:
    """Normalize summary_data() from a shekel budget context."""
    total = raw.get("total_cost")
    if total is None:
        total = raw.get("total_spent", 0)
    by_model = raw.get("by_model") or {}
    return {
        "total_cost": float(total or 0),
        "by_model": by_model,
    }
