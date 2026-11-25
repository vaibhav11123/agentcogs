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


def lanes_from_usage(provider: str, usage: dict) -> dict:
    """Map a provider usage object onto exclusive token lanes.

    The returned lanes are additive. This function does not price them.
    """
    name = (provider or "").lower()
    if name == "openai":
        # Chat Completions reports prompt_tokens. The Responses API reports
        # input_tokens. Cached and cache-write tokens are subsets of that total.
        details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        cache_read = int(details.get("cached_tokens") or 0)
        write_details = usage.get("cache_write_tokens_details") or {}
        if "ttl_30m_tokens" in write_details or "ttl_12h_tokens" in write_details:
            write_30m = int(write_details.get("ttl_30m_tokens") or 0)
            write_12h = int(write_details.get("ttl_12h_tokens") or 0)
        elif "cache_write_tokens" in usage:
            write_30m = int(usage.get("cache_write_tokens") or 0)
            write_12h = 0
        else:
            write_30m = int(details.get("cache_write_tokens") or 0)
            write_12h = 0
        if "input_tokens" in usage and usage.get("input_tokens") is not None:
            reported = int(usage.get("input_tokens") or 0)
        else:
            reported = int(usage.get("prompt_tokens") or 0)
        uncached = reported - cache_read - write_30m - write_12h
        if uncached < 0:
            raise ValueError("LANE_NEGATIVE")
        if "output_tokens" in usage and usage.get("output_tokens") is not None:
            output = int(usage.get("output_tokens") or 0)
            reasoning = usage.get("output_tokens_details") or {}
        else:
            output = int(usage.get("completion_tokens") or 0)
            reasoning = usage.get("completion_tokens_details") or {}
        return {
            "uncached_input": uncached,
            "cache_read": cache_read,
            "cache_write_5m": 0,
            "cache_write_1h": 0,
            "cache_write_30m": write_30m,
            "cache_write_12h": write_12h,
            "output": output,
            "reasoning": int(reasoning.get("reasoning_tokens") or 0),
        }
    if name in {"anthropic", "claude"}:
        creation = usage.get("cache_creation") or {}
        if "ephemeral_5m_input_tokens" in creation or "ephemeral_1h_input_tokens" in creation:
            write_5m = int(creation.get("ephemeral_5m_input_tokens") or 0)
            write_1h = int(creation.get("ephemeral_1h_input_tokens") or 0)
        else:
            write_5m = int(usage.get("cache_creation_input_tokens") or 0)
            write_1h = 0
        return {
            "uncached_input": int(usage.get("input_tokens") or 0),
            "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_write_5m": write_5m,
            "cache_write_1h": write_1h,
            "cache_write_30m": 0,
            "cache_write_12h": 0,
            "output": int(usage.get("output_tokens") or 0),
            "reasoning": 0,
        }
    raise ValueError("LANE_NEGATIVE")


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
