"""Connectivity check — verify API key and endpoint before first run()."""
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import get_config
from .errors import ConfigurationError, PingError


@dataclass(frozen=True)
class PingResult:
    ok: bool
    workspace_id: str
    plan: str
    server_time: Optional[int] = None


def ping(timeout_seconds: Optional[float] = None) -> PingResult:
    """Verify API key, workspace, and reachability.

    Requires prior agentcogs.init() (or AGENTCOGS_* env vars).
    """
    cfg = get_config()
    if cfg.offline:
        raise PingError(
            "ping() is not available in offline mode. Set offline=False and provide api_key."
        )
    if not cfg.api_key:
        raise ConfigurationError(
            "agentcogs.init() requires api_key (or AGENTCOGS_API_KEY env)."
        )

    timeout = timeout_seconds if timeout_seconds is not None else cfg.timeout_seconds
    try:
        resp = httpx.get(
            f"{cfg.endpoint}/v1/sdk/ping",
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "User-Agent": _user_agent(),
            },
            timeout=timeout,
        )
    except httpx.ConnectError as e:
        raise PingError(
            f"Cannot reach AgentCOGS API at {cfg.endpoint}. "
            f"Check AGENTCOGS_ENDPOINT and network. ({e})"
        ) from e
    except httpx.TimeoutException as e:
        raise PingError(
            f"AgentCOGS API timed out after {timeout}s ({cfg.endpoint})."
        ) from e

    if resp.status_code == 401:
        raise PingError(
            "Invalid API key. Copy the key from Settings in the dashboard."
        )
    if resp.status_code == 404:
        raise PingError(
            f"SDK ping endpoint not found at {cfg.endpoint}. "
            "Check AGENTCOGS_ENDPOINT (e.g. http://localhost:8000 for local dev)."
        )
    if resp.status_code >= 400:
        raise PingError(f"ping failed: HTTP {resp.status_code} — {resp.text[:200]}")

    data = resp.json()
    return PingResult(
        ok=bool(data.get("ok", True)),
        workspace_id=str(data["workspace_id"]),
        plan=str(data.get("plan", "free")),
        server_time=data.get("server_time"),
    )


def _user_agent() -> str:
    from ._version import __version__

    return f"agentcogs-python/{__version__}"
