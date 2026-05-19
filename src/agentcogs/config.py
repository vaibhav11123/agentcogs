import os
from dataclasses import dataclass
from typing import Optional
from .errors import ConfigurationError


@dataclass
class _Config:
    api_key: Optional[str] = None
    workspace_id: Optional[str] = None
    endpoint: str = "https://api.agentcogs.dev"
    timeout_seconds: float = 2.0
    offline: bool = False  # if True, only writes to outbox


_config = _Config()


def init(
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    offline: bool = False,
    timeout_seconds: float = 2.0,
) -> None:
    """Initialise the AgentCOGS SDK.

    Reads from env vars as fallback:
      AGENTCOGS_API_KEY, AGENTCOGS_WORKSPACE_ID, AGENTCOGS_ENDPOINT
    """
    _config.api_key = api_key or os.environ.get("AGENTCOGS_API_KEY")
    _config.workspace_id = workspace_id or os.environ.get("AGENTCOGS_WORKSPACE_ID")
    _config.endpoint = (
        endpoint
        or os.environ.get("AGENTCOGS_ENDPOINT")
        or "https://api.agentcogs.dev"
    ).rstrip("/")
    _config.offline = offline or os.environ.get("AGENTCOGS_OFFLINE") == "1"
    _config.timeout_seconds = timeout_seconds

    if not _config.offline and not _config.api_key:
        raise ConfigurationError(
            "agentcogs.init() requires api_key (or AGENTCOGS_API_KEY env). "
            "For local dev without backend, pass offline=True."
        )


def get_config() -> _Config:
    if _config.api_key is None and not _config.offline:
        # Auto-init from env if user forgot to call init()
        init()
    return _config
