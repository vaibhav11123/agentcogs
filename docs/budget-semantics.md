# What the budget check does

`agentcogs.run()` asks, before it enters the block, whether this customer is already over `monthly_budget_usd`. If the status is already `exceeded`, it raises `CustomerBudgetExceededError` and does not enter the block.

That is a pre-check, not an atomic reservation.

- Two calls already in flight can both pass the check. Both can spend.
- A LiteLLM callback records `response_cost` after the provider has answered, so it cannot stop that call. LiteLLM does not ship the callback. You copy it from this repository.
- Ingest does not block the model call. A failed post sits in the local outbox and is retried.
- The check does not include people, infrastructure, or the rest of the bill. It compares attributed AI cost already stored for this customer with the budget you set.

The margin on the customer page is a different number. It is the fee minus attributed AI cost. See [cost-methodology.md](cost-methodology.md).
