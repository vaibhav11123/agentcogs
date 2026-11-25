# What the budget check does

`agentcogs.run()` asks, before it enters the block, whether this customer is already over `monthly_budget_usd`. Enforcement stays off until the workspace turns it on. While it is off, an exceeded budget does not stop the block. The would-be block is recorded and the request continues. When the workspace turns enforcement on, an exceeded status raises `CustomerBudgetExceededError` and does not enter the block.

The local ledger is a different path. `agentcogs init` stores `budget_enforce` as false and records the sample. `agentcogs status` and `agentcogs export` show that flag. `agentcogs budget` prints a recommendation and leaves the flag false. Those commands do not raise `CustomerBudgetExceededError`.

That is a pre-check, not an atomic reservation.

- Two calls already in flight can both pass the check. Both can spend.
- A LiteLLM callback records `response_cost` after the provider has answered, so it cannot stop that call. LiteLLM does not ship the callback. You copy it from this repository.
- Ingest does not block the model call. A failed post sits in the local outbox and is retried.
- The check does not include people, infrastructure, or the rest of the bill. It compares attributed AI cost already stored for this customer with the budget you set.

The margin on the customer page is a different number. It is the fee minus attributed AI cost. See [cost-methodology.md](cost-methodology.md).
