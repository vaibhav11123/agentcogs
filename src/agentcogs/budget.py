"""The agentcogs.run() context manager — the SDK's entire public surface."""
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional

from shekel import budget as shekel_budget

from .client import emit_event, fetch_budget
from .config import get_config
from .errors import ConfigurationError, CustomerBudgetExceededError
from .tokens import normalize_summary


@contextmanager
def run(
    customer_id: str,
    workflow_id: str = "default",
    workspace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Iterator[object]:
    """Wrap any block of LLM-using code with per-customer cost tracking.

    On entry: checks remote budget. Raises CustomerBudgetExceededError
        BEFORE any LLM call fires if cap is reached.

    On exit: builds a cost event from Shekel's summary and POSTs
        it asynchronously. Never blocks user code on network I/O.

    Example:
        with agentcogs.run(customer_id="cust_42", workflow_id="summarize"):
            result = my_langgraph_agent.invoke({"input": "..."})
    """
    cfg = get_config()
    ws_id = workspace_id or cfg.workspace_id
    if not ws_id and not cfg.offline:
        raise ConfigurationError(
            "workspace_id required: pass workspace_id= or set in init()"
        )

    run_id = str(uuid.uuid4())

    # 1. Pre-flight budget check.
    b = fetch_budget(ws_id or "offline", customer_id)
    if b["status"] == "exceeded":
        raise CustomerBudgetExceededError(
            customer_id=customer_id,
            spent_usd=b["spent_usd"],
            budget_usd=b["budget_usd"],
        )

    remaining = b.get("remaining_usd")
    max_usd = float(remaining) if remaining and remaining != float("inf") else None

    status = "completed"
    error_msg: Optional[str] = None

    # 2. Enter Shekel budget context.
    kwargs = {"name": customer_id}
    if max_usd is not None:
        kwargs["max_usd"] = max_usd

    with shekel_budget(**kwargs) as ctx:
        try:
            yield ctx
        except CustomerBudgetExceededError:
            status = "budget_exceeded"
            raise
        except Exception as e:
            status = "error"
            error_msg = str(e)[:500]
            raise
        finally:
            # 3. Capture cost summary.
            try:
                summary = ctx.summary_data()
                event = {
                    "run_id": run_id,
                    "workspace_id": ws_id or "offline",
                    "customer_id": customer_id,
                    "workflow_id": workflow_id,
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
                # 4. Fire-and-forget delivery.
                threading.Thread(
                    target=emit_event, args=(event,), daemon=True
                ).start()
            except Exception:
                # Never let telemetry break user code.
                pass
