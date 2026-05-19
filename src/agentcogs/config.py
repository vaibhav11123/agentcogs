import atexit
import os
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

from .errors import ConfigurationError

BudgetMode = Literal["open", "closed"]


@dataclass
class _Config:
    api_key: Optional[str] = None
    workspace_id: Optional[str] = None
    endpoint: str = "https://api.agentcogs.dev"
    timeout_seconds: float = 2.0
    offline: bool = False
    budget_mode: BudgetMode = "open"
    max_ingest_workers: int = 4
    register_atexit: bool = True
    on_telemetry_error: Optional[Callable[[Exception], None]] = None
    _atexit_registered: bool = field(default=False, repr=False)


_config = _Config()


def init(
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    offline: bool = False,
    timeout_seconds: float = 2.0,
    budget_mode: BudgetMode = "open",
    max_ingest_workers: int = 4,
    register_atexit: bool = True,
    on_telemetry_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """Initialise the AgentCOGS SDK.

    Reads from env vars as fallback:
      AGENTCOGS_API_KEY, AGENTCOGS_WORKSPACE_ID, AGENTCOGS_ENDPOINT,
      AGENTCOGS_OFFLINE, AGENTCOGS_BUDGET_MODE (open|closed)
    """
    from . import client as _client_mod

    _client_mod.reset_client()

    _config.api_key = api_key or os.environ.get("AGENTCOGS_API_KEY")
    _config.workspace_id = workspace_id or os.environ.get("AGENTCOGS_WORKSPACE_ID")
    _config.endpoint = (
        endpoint
        or os.environ.get("AGENTCOGS_ENDPOINT")
        or "https://api.agentcogs.dev"
    ).rstrip("/")
    _config.offline = offline or os.environ.get("AGENTCOGS_OFFLINE") == "1"
    _config.timeout_seconds = timeout_seconds
    env_budget = os.environ.get("AGENTCOGS_BUDGET_MODE", "").lower()
    if env_budget in ("open", "closed"):
        _config.budget_mode = env_budget  # type: ignore[assignment]
    else:
        _config.budget_mode = budget_mode
    _config.max_ingest_workers = max(1, max_ingest_workers)
    _config.register_atexit = register_atexit
    _config.on_telemetry_error = on_telemetry_error

    if not _config.offline and not _config.api_key:
        raise ConfigurationError(
            "agentcogs.init() requires api_key (or AGENTCOGS_API_KEY env). "
            "For local dev without backend, pass offline=True."
        )

    if register_atexit and not _config._atexit_registered:
        atexit.register(_shutdown_on_exit)
        _config._atexit_registered = True


def get_config() -> _Config:
    if _config.api_key is None and not _config.offline:
        init()
    return _config


def _shutdown_on_exit() -> None:
    try:
        from .shutdown import shutdown

        shutdown(drain_timeout=5.0)
    except Exception:
        pass
