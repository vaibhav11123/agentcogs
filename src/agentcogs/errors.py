class AgentCOGSError(Exception):
    """Base exception for all AgentCOGS errors."""


class ConfigurationError(AgentCOGSError):
    """Raised when SDK is used without init() or with bad config."""


class CustomerBudgetExceededError(AgentCOGSError):
    """Raised when a customer's monthly budget cap is reached.

    Raised on context entry BEFORE any LLM call fires, so zero
    provider charges are incurred.

    Attributes:
        customer_id: External customer identifier
        spent_usd:   Current month-to-date spend
        budget_usd:  Configured monthly cap
    """

    def __init__(self, customer_id: str, spent_usd: float, budget_usd: float):
        self.customer_id = customer_id
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        super().__init__(
            f"Customer '{customer_id}' exceeded budget: "
            f"${spent_usd:.2f} / ${budget_usd:.2f}"
        )
