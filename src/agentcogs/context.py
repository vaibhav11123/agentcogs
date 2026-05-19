"""Request-scoped customer/workflow attribution via contextvars."""
from contextvars import ContextVar
from typing import Optional

_customer_id: ContextVar[Optional[str]] = ContextVar("agentcogs_customer_id", default=None)
_workflow_id: ContextVar[Optional[str]] = ContextVar("agentcogs_workflow_id", default=None)


def set_customer(customer_id: Optional[str]) -> None:
    """Set billing customer for the current async/thread context."""
    _customer_id.set(customer_id)


def set_workflow(workflow_id: Optional[str]) -> None:
    """Set default workflow id for subsequent run() calls in this context."""
    _workflow_id.set(workflow_id)


def get_customer() -> Optional[str]:
    return _customer_id.get()


def get_workflow() -> Optional[str]:
    return _workflow_id.get()


def resolve_customer(explicit: Optional[str]) -> Optional[str]:
    if explicit is not None:
        return explicit
    return get_customer()


def resolve_workflow(explicit: Optional[str], default: str = "default") -> str:
    if explicit is not None:
        return explicit
    return get_workflow() or default
