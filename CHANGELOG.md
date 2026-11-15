# Changelog

## 0.1.1

- SDK-only sdist for the first PyPI upload. Tag `v0.1.0` built, and PyPI refused it because the trusted publisher was not saved.

## 0.1.0

- Per-customer LLM cost attribution with `set_customer()` + `run()`
- Runtime budget enforcement via `CustomerBudgetExceededError`
- Offline-safe SQLite outbox for ingest retry
- Anthropic cache token normalization (input + cache read + cache creation)
- FastAPI / Starlette middleware integrations
- Shekel `>=1.2,<2` compatibility layer
