"""Attribution helpers. They do not read prompts, responses, or provider keys."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator, Optional, TypeVar

from .context import get_customer, set_customer
from .errors import ConfigurationError

T = TypeVar("T")


@contextmanager
def customer(customer_id: str) -> Iterator[str]:
    previous = get_customer()
    set_customer(customer_id)
    try:
        yield customer_id
    finally:
        set_customer(previous)


def instrument(callback: Optional[Callable[..., T]] = None) -> Callable[..., T] | dict:
    """Wrap a call so it refuses to run without a customer. No provider SDK is imported."""
    if callback is None:
        return {"prompts": False, "provider_keys": False, "customer_required": True}

    def wrapped(*args, **kwargs):
        if not get_customer():
            raise ConfigurationError("Identify customer context before the call")
        return callback(*args, **kwargs)

    return wrapped
