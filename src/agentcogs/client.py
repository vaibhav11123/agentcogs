"""HTTP client. Fire-and-forget POST to ingest endpoint.

Never blocks user code. Failures route to outbox for retry.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple

import httpx

from ._version import __version__
from .config import get_config
from .errors import AgentCOGSError
from .outbox import drain, enqueue

log = logging.getLogger("agentcogs")

_client: Optional[httpx.Client] = None
_executor: Optional[ThreadPoolExecutor] = None


def _user_agent() -> str:
    return f"agentcogs-python/{__version__}"


def _default_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {get_config().api_key}",
        "User-Agent": _user_agent(),
        "Content-Type": "application/json",
        "X-AgentCOGS-SDK-Version": __version__,
    }


def reset_client() -> None:
    """Close httpx client (e.g. on re-init)."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        cfg = get_config()
        _client = httpx.Client(
            base_url=cfg.endpoint,
            headers=_default_headers(),
            timeout=cfg.timeout_seconds,
        )
    return _client


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        cfg = get_config()
        _executor = ThreadPoolExecutor(
            max_workers=cfg.max_ingest_workers,
            thread_name_prefix="agentcogs-ingest",
        )
    return _executor


def shutdown_executor(wait: bool = True, timeout: float = 10.0) -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=wait, cancel_futures=not wait)
        _executor = None


def _post(event: Dict[str, Any]) -> None:
    """Synchronous POST. Raises on any failure."""
    cfg = get_config()
    if cfg.offline:
        log.debug("offline mode — event %s skipped", event["run_id"])
        return
    resp = _get_client().post("/v1/ingest", json=event)
    resp.raise_for_status()


def emit_event_sync(event: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Synchronous ingest. Returns (accepted, error_message)."""
    try:
        drain(_post, max_items=20)
    except Exception as e:
        log.debug("outbox drain failed: %s", e)
    try:
        _post(event)
        return True, None
    except Exception as e:
        enqueue(event)
        return False, str(e)


def emit_event(event: Dict[str, Any]) -> None:
    """Best-effort delivery via thread pool. Always returns quickly."""

    def _work() -> None:
        try:
            drain(_post, max_items=20)
        except Exception as e:
            log.debug("outbox drain failed: %s", e)
        try:
            _post(event)
        except Exception as e:
            log.warning("ingest failed (%s) — queued for retry", e)
            enqueue(event)

    _get_executor().submit(_work)


def fetch_budget(workspace_id: str, customer_id: str) -> Dict[str, Any]:
    """Pre-flight budget check. Fail-open unless budget_mode=closed."""
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
        if cfg.budget_mode == "closed":
            raise AgentCOGSError(
                f"Budget check failed and budget_mode=closed: {e}"
            ) from e
        log.warning("budget fetch failed (%s) — failing open", e)
        return {
            "status": "ok",
            "spent_usd": 0.0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }
