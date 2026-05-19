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
- Production: omit `AGENTCOGS_ENDPOINT` (defaults to `https://api.agentcogs.dev`).

## Costs show as $0.0000

Sub-cent amounts need 6 decimal display (dashboard). Ensure the model is supported by Shekel or pass `price_per_1k_tokens` to `run()`.

## CustomerBudgetExceededError on demo data

Seeded demo customers may be over budget. Use a fresh `customer_id` / `AGENTCOGS_TEST_TENANT` or reset with `./tools/seed_demo.sh`.

## Budget not blocking

Budget caps apply only after `monthly_budget_usd` is set in the dashboard. Budget API fail-open is default (`budget_mode="open"` or `AGENTCOGS_BUDGET_MODE=open`).

## Mock demo vs real ingest

| Symptom | Cause |
|---------|--------|
| JSON in terminal, empty dashboard | Ran `prototype/demo.py` (mock) instead of `examples/hello_agentcogs.py` |
| Shekel output only | Ran `prototype.py` (no AgentCOGS package ingest) |

See [docs/README.md](README.md) for which script to use.
