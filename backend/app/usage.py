"""Coarse dashboard-screen events for PostHog.

A request is sent only when POSTHOG_PROJECT_API_KEY is set and CI is unset.
The body is the screen name, this API's package version, and success or failure.
Prompts, customer names, API keys, and amounts are not properties.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

PACKAGE_VERSION = "0.1.0"
_EVENT = "product_usage"
_DEFAULT_ORIGIN = "https://us.i.posthog.com"
_TIMEOUT_SECONDS = 2.0
SCREENS = frozenset(
    {
        "login",
        "demo",
        "onboarding",
        "customers",
        "customer",
        "alerts",
        "settings",
    }
)


async def capture_screen(*, screen: str, success: bool) -> None:
    """POST one anonymous screen event. Failures here never leave this function."""
    prepared = _prepare(screen=screen, success=success)
    if prepared is None:
        return
    url, body = prepared
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, follow_redirects=False) as client:
            await client.post(url, json=body)
    except Exception:  # noqa: BLE001 — a usage outage must not fail the API
        return


def _prepare(*, screen: str, success: bool) -> tuple[str, dict] | None:
    if os.environ.get("CI", "").strip():
        return None
    api_key = os.environ.get("POSTHOG_PROJECT_API_KEY", "").strip()
    if not api_key or screen not in SCREENS:
        return None
    origin = _origin()
    if origin is None:
        return None
    return f"{origin}/i/v0/e/", _body(api_key=api_key, screen=screen, success=success)


def _origin() -> str | None:
    raw = os.environ.get("POSTHOG_HOST", "").strip() or _DEFAULT_ORIGIN
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _body(*, api_key: str, screen: str, success: bool) -> dict:
    return {
        "api_key": api_key,
        "event": _EVENT,
        "distinct_id": str(uuid.uuid4()),
        "properties": {
            "screen": screen,
            "package_version": PACKAGE_VERSION,
            "outcome": "success" if success else "failure",
            "$process_person_profile": False,
        },
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
