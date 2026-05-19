"""AgentCOGS — per-customer LLM cost attribution.

Quickstart:
    import agentcogs
    agentcogs.init(api_key="acg_live_...", workspace_id="...")

    agentcogs.set_customer("tenant_42")  # once per request
    with agentcogs.run(workflow_id="summarize"):
        # any openai / anthropic / langgraph code here
        ...
"""
from ._version import __version__
from .budget import IngestStatus, RunContext, run
from .config import init
from .context import get_customer, get_workflow, set_customer, set_workflow
from .errors import (
    AgentCOGSError,
    ConfigurationError,
    CustomerBudgetExceededError,
    PingError,
)
from .ping import PingResult, ping
from .shutdown import ShutdownResult, shutdown

__all__ = [
    "__version__",
    "init",
    "run",
    "ping",
    "shutdown",
    "set_customer",
    "set_workflow",
    "get_customer",
    "get_workflow",
    "RunContext",
    "IngestStatus",
    "PingResult",
    "ShutdownResult",
    "AgentCOGSError",
    "CustomerBudgetExceededError",
    "ConfigurationError",
    "PingError",
]
