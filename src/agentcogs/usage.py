"""Coarse product-usage events for PostHog.

A request is sent only when POSTHOG_PROJECT_API_KEY is set and CI is unset.
The body is the command name, the package version, and success or failure.
Prompts, customer names, API keys, and amounts are not properties.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from ._version import __version__

_EVENT = "product_usage"
_DEFAULT_ORIGIN = "https://us.i.posthog.com"
_TIMEOUT_SECONDS = 2.0
COMMANDS = frozenset({"outbox status", "unrecognized"})


def capture_usage(*, command: str, success: bool) -> None:
    """POST one anonymous usage event. Failures here never leave this function."""
    prepared = _prepare(command=command, success=success)
    if prepared is None:
        return
    url, body = prepared
    try:
        httpx.post(url, json=body, timeout=_TIMEOUT_SECONDS, follow_redirects=False)
    except Exception:  # noqa: BLE001 — a usage outage must not fail the command
        return


def _prepare(*, command: str, success: bool) -> tuple[str, dict] | None:
    if os.environ.get("CI", "").strip():
        return None
    api_key = os.environ.get("POSTHOG_PROJECT_API_KEY", "").strip()
    if not api_key or command not in COMMANDS:
        return None
    origin = _origin()
    if origin is None:
        return None
    return f"{origin}/i/v0/e/", _body(api_key=api_key, command=command, success=success)


def _origin() -> str | None:
    raw = os.environ.get("POSTHOG_HOST", "").strip() or _DEFAULT_ORIGIN
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _body(*, api_key: str, command: str, success: bool) -> dict:
    return {
        "api_key": api_key,
        "event": _EVENT,
        "distinct_id": str(uuid.uuid4()),
        "properties": {
            "command": command,
            "package_version": __version__,
            "outcome": "success" if success else "failure",
            "$process_person_profile": False,
        },
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
