"""The agentcogs.run() context manager — the SDK's entire public surface."""
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator, Optional

from shekel import budget as shekel_budget

from .client import emit_event, emit_event_sync, fetch_budget
from .config import get_config
from .context import resolve_customer, resolve_workflow
from .errors import ConfigurationError, CustomerBudgetExceededError
from .tokens import normalize_summary

log = logging.getLogger("agentcogs")


@dataclass
class IngestStatus:
    accepted: bool
    duplicate: bool = False
    error: Optional[str] = None


class RunContext:
    """Handle returned from agentcogs.run()."""

    def __init__(
        self,
        shekel_ctx: object,
        run_id: str,
        customer_id: str,
        workflow_id: str,
    ):
        self._shekel = shekel_ctx
        self.run_id = run_id
        self.customer_id = customer_id
        self.workflow_id = workflow_id
        self._event: Optional[dict] = None

    def summary_data(self) -> dict:
        return self._shekel.summary_data()  # type: ignore[attr-defined]

    def wait_for_ingest(self, timeout: float = 5.0) -> IngestStatus:
        """Block until event is POSTed (onboarding/tests). Uses sync ingest."""
        if self._event is None:
            return IngestStatus(accepted=False, error="no event built yet")
        ok, err = emit_event_sync(self._event)
        return IngestStatus(accepted=ok, error=err)

    def __getattr__(self, name: str):
        return getattr(self._shekel, name)


@contextmanager
def run(
    customer_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    price_per_1k_tokens: Optional[Dict[str, float]] = None,
) -> Iterator[RunContext]:
    """Wrap any block of LLM-using code with per-customer cost tracking.

    customer_id may be omitted if agentcogs.set_customer() was called for this context.
    workflow_id defaults to set_workflow() context value, else "default".
    """
    cfg = get_config()
    ws_id = workspace_id or cfg.workspace_id
    if not ws_id and not cfg.offline:
        raise ConfigurationError(
            "workspace_id required: pass workspace_id= or set in init()"
        )

    resolved_customer = resolve_customer(customer_id)
    if not resolved_customer:
        raise ConfigurationError(
            "customer_id required: pass customer_id= to run() or call "
            "set_customer() in middleware before agent code. "
            "See docs/concepts/customer-id.md"
        )
    resolved_workflow = resolve_workflow(workflow_id)

    run_id = str(uuid.uuid4())

    b = fetch_budget(ws_id or "offline", resolved_customer)
    if b["status"] == "exceeded":
        raise CustomerBudgetExceededError(
            customer_id=resolved_customer,
            spent_usd=b["spent_usd"],
            budget_usd=b["budget_usd"],
        )

    remaining = b.get("remaining_usd")
    max_usd = float(remaining) if remaining and remaining != float("inf") else None

    status = "completed"
    error_msg: Optional[str] = None

    kwargs: dict = {"name": resolved_customer}
    if max_usd is not None:
        kwargs["max_usd"] = max_usd
    if price_per_1k_tokens is not None:
        kwargs["price_per_1k_tokens"] = price_per_1k_tokens

    run_ctx: Optional[RunContext] = None

    with shekel_budget(**kwargs) as ctx:
        try:
            run_ctx = RunContext(ctx, run_id, resolved_customer, resolved_workflow)
            yield run_ctx
        except CustomerBudgetExceededError:
            status = "budget_exceeded"
            raise
        except Exception as e:
            status = "error"
            error_msg = str(e)[:500]
            raise
        finally:
            try:
                summary = ctx.summary_data()
                event = {
                    "run_id": run_id,
                    "workspace_id": ws_id or "offline",
                    "customer_id": resolved_customer,
                    "workflow_id": resolved_workflow,
                    "ts": int(time.time()),
                    "status": status,
                    "total_usd": float(
                        summary.get("total_cost") or summary.get("total_spent") or 0
                    ),
                    "models": normalize_summary(summary.get("by_model", {})),
                    "node_costs": getattr(ctx, "node_costs", {}),
                    "metadata": metadata or {},
                    "error": error_msg,
                }
                if run_ctx is not None:
                    run_ctx._event = event
                emit_event(event)
            except Exception as e:
                log.warning("telemetry failed", exc_info=True)
                cb = cfg.on_telemetry_error
                if cb is not None:
                    try:
                        cb(e)
                    except Exception:
                        pass
