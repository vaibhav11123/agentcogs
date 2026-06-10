# Changelog

## 0.1.0

- Per-customer LLM cost attribution with `set_customer()` + `run()`
- Runtime budget enforcement via `CustomerBudgetExceededError`
- Offline-safe SQLite outbox for ingest retry
- Anthropic cache token normalization (input + cache read + cache creation)
- FastAPI / Starlette middleware integrations
- Shekel `>=1.2,<2` compatibility layer
