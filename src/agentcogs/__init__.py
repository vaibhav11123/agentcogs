"""AgentCOGS — per-customer LLM cost attribution.

Quickstart:
    import agentcogs
    agentcogs.init(api_key="acg_live_...")

    with agentcogs.run(customer_id="cust_42"):
        # any openai / anthropic / langgraph code here
        ...
"""
from ._version import __version__
from .budget import run
from .config import init
from .errors import (
    AgentCOGSError,
    CustomerBudgetExceededError,
    ConfigurationError,
)

__all__ = [
    "__version__",
    "init",
    "run",
    "AgentCOGSError",
    "CustomerBudgetExceededError",
    "ConfigurationError",
]
