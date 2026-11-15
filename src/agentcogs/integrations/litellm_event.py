"""Build an /v1/ingest body from a LiteLLM callback kwargs dict.

LiteLLM reports OpenAI-style usage (prompt_tokens, completion_tokens).
A raw provider response uses input_tokens and output_tokens. Both are accepted.
"""
from __future__ import annotations

import time
import uuid
from typing import Any


def _usage_int(usage: Any, *keys: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        for key in keys:
            value = usage.get(key)
            if value:
                return int(value)
        return 0
    for key in keys:
        value = getattr(usage, key, None)
        if value:
            return int(value)
    return 0


def build_ingest_event(
    kwargs: dict,
    *,
    status: str,
    error: str | None = None,
    workspace_id: str | None = None,
) -> dict | None:
    """Return an ingest body, or None when the call has no customer."""
    meta = kwargs.get("metadata") or {}
    customer_id = kwargs.get("user") or meta.get("agentcogs_customer_id")
    if not customer_id:
        return None

    model = kwargs.get("model") or "unknown"
    cost = float(kwargs.get("response_cost") or 0)
    usage = kwargs.get("usage")
    start = kwargs.get("start_time")
    ts = int(start.timestamp()) if start is not None and hasattr(start, "timestamp") else int(time.time())
    event = {
        "run_id": str(uuid.uuid4()),
        "customer_id": str(customer_id),
        "workflow_id": meta.get("agentcogs_workflow_id") or "default",
        "ts": ts,
        "status": status,
        "total_usd": max(cost, 0.0),
        "models": {
            model: {
                "input_tokens": _usage_int(usage, "prompt_tokens", "input_tokens"),
                "output_tokens": _usage_int(usage, "completion_tokens", "output_tokens"),
                "usd": max(cost, 0.0),
            }
        },
        "node_costs": {},
        "metadata": {"source": "litellm"},
        "error": error,
    }
    if workspace_id:
        event["workspace_id"] = workspace_id
    return event
