# Changelog

## 0.1.3

- The public description leads with customer-level AI unit economics: which fees still cover attributed AI cost.
- AI margin is defined as the fee after that cost. It is not total customer profitability.

## 0.1.2

- The project description uses absolute image URLs, so the Patternstack stills load on PyPI, and a short GIF shows the fictional sample opening onto Vellum Research.
- The README separates the sample, self-host, and the fact that no hosted API is serving. It shows where the cost comes from (`examples/hello_agentcogs.py`) and defines AI margin as the fee minus attributed AI cost.
- The budget check is documented as a pre-call guardrail. Two calls already in flight can both pass.
- `starlette` moved to the `integrations` extra. The SDK endpoint defaults to `http://localhost:8000`.
- PyPI uses `PYPI.md`, a package description, instead of the repository README. The project homepage is the working sample at https://agentcogs.vercel.app.

## 0.1.1

- SDK-only sdist for the first PyPI upload. Tag `v0.1.0` built, and PyPI refused it because the trusted publisher was not saved.

## 0.1.0

- Per-customer LLM cost attribution with `set_customer()` + `run()`
- Runtime budget enforcement via `CustomerBudgetExceededError`
- Offline-safe SQLite outbox for ingest retry
- Anthropic cache token normalization (input + cache read + cache creation)
- FastAPI / Starlette middleware integrations
- Shekel `>=1.2,<2` compatibility layer
