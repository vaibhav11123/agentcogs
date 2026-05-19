"""Graceful shutdown — drain outbox and close HTTP resources."""
from dataclasses import dataclass

from .client import emit_event_sync, reset_client, shutdown_executor
from .outbox import drain, get_status


@dataclass(frozen=True)
class ShutdownResult:
    outbox_sent: int
    outbox_failed: int
    outbox_pending: int
    outbox_dead: int


def shutdown(drain_timeout: float = 10.0) -> ShutdownResult:
    """Drain outbox, shut down ingest pool, close httpx client."""
    from .config import get_config
    from .client import _post

    cfg = get_config()
    sent = failed = 0
    if not cfg.offline:
        try:
            sent, failed = drain(_post, max_items=500)
        except Exception:
            pass

    shutdown_executor(wait=True, timeout=drain_timeout)
    reset_client()

    st = get_status()
    return ShutdownResult(
        outbox_sent=sent,
        outbox_failed=failed,
        outbox_pending=st["pending"],
        outbox_dead=st["dead"],
    )
