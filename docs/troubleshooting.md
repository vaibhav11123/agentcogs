# SDK troubleshooting

## Empty dashboard after installing

- Installing the SDK does not send data until `agentcogs.run()` executes (with LLM work or a zero-cost test run).
- Run `agentcogs.ping()` after `init()` to verify API key, workspace id, and endpoint.
- Use `examples/hello_agentcogs.py` with `AGENTCOGS_API_KEY`, `AGENTCOGS_WORKSPACE_ID`, and correct `AGENTCOGS_ENDPOINT`.
- Check `python -m agentcogs outbox status` for pending or failed ingests.
- Call `agentcogs.shutdown()` before exit in scripts so the outbox flushes.

## ConfigurationError: workspace_id required

Pass `workspace_id=` to `init()` or set `AGENTCOGS_WORKSPACE_ID`.

## ConfigurationError: customer_id required

Call `set_customer(tenant_id)` before `run()`, or pass `customer_id=` to `run()`.

## PingError / connection refused

- Local API: `AGENTCOGS_ENDPOINT=http://localhost:8000` and backend running (`./tools/start_demo.sh` or `uvicorn`).
- Set `AGENTCOGS_ENDPOINT` to the API you are running. The package default host is not serving a public API right now.

## Costs show as $0.0000

`agentcogs init` does not post zero. `agentcogs status` shows `incurred_micro` 24600 for the one sample event, which is $0.0246. A `run()` block that makes no instrumented call still posts zero. The local ledger does not look up a live provider price.

## CustomerBudgetExceededError on demo data

The local commands do not raise this. `agentcogs init` stores `budget_enforce` false and records the sample. Seeded demo customers in a self-hosted stack can already be over a cap you set. Use a fresh `customer_id` or reset with `./tools/seed_demo.sh`.

## Budget not blocking

That is the default. `agentcogs init` stores `budget_enforce` false. `agentcogs status` and `agentcogs export` show the flag. `agentcogs budget` prints a recommendation and leaves the flag false. None of those commands stops the sample.

`budget_mode` is a different switch. It only applies when the budget request itself fails. The default is `open`, so a failed request does not stop the block. Setting it to `closed` does not turn ledger enforcement on.

## Inspect the local ledger

```bash
pip install agentcogs
agentcogs init
agentcogs doctor
agentcogs status
agentcogs export
```

`init` writes `.agentcogs/ledger.sqlite` and one priced sample. `doctor` prints `ok`. `status` prints the counts. `export` prints those counts and the events. None of these calls a model.

With no API key, a call inside `agentcogs.run(customer_id=...)` is priced from the response and added to that file. `examples/own_customer.py` does this for customer `acme` against a stand-in. `instrument()` does not write a row.

`prototype/demo.py` prints a mock. It does not write this ledger.

See [LOCAL.md](LOCAL.md).
