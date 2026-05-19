"""HTTP client. Fire-and-forget POST to ingest endpoint.

Never blocks user code. Failures route to outbox for retry.
"""
import logging
import threading
from typing import Any, Dict

import httpx

from .config import get_config
from .outbox import drain, enqueue

log = logging.getLogger("agentcogs")

# Singleton client, reused across calls (connection pooling).
_client_lock = threading.Lock()
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None:
            cfg = get_config()
            _client = httpx.Client(
                base_url=cfg.endpoint,
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "User-Agent": "agentcogs-python/0.1.0",
                    "Content-Type": "application/json",
                },
                timeout=cfg.timeout_seconds,
            )
        return _client


def _post(event: Dict[str, Any]) -> None:
    """Synchronous POST. Raises on any failure."""
    cfg = get_config()
    if cfg.offline:
        log.debug("offline mode — event %s skipped", event["run_id"])
        return
    resp = _get_client().post("/v1/ingest", json=event)
    resp.raise_for_status()


def emit_event(event: Dict[str, Any]) -> None:
    """Best-effort delivery. Always returns. Runs in background thread."""
    # 1. Try to drain any backlog opportunistically.
    try:
        drain(_post, max_items=20)
    except Exception as e:
        log.debug("outbox drain failed: %s", e)

    # 2. Try to send this event directly.
    try:
        _post(event)
    except Exception as e:
        log.warning("ingest failed (%s) — queued for retry", e)
        enqueue(event)


def fetch_budget(workspace_id: str, customer_id: str) -> Dict[str, Any]:
    """Pre-flight budget check. Returns sensible defaults on failure
    so user code is never blocked by AgentCOGS being down."""
    cfg = get_config()
    if cfg.offline:
        return {
            "status": "ok",
            "spent_usd": 0.0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }
    try:
        resp = _get_client().get(
            "/v1/budget",
            params={"workspace": workspace_id, "customer": customer_id},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning("budget fetch failed (%s) — failing open", e)
        return {
            "status": "ok",
            "spent_usd": 0.0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }
