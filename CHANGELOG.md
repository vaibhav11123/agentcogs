# Changelog

## 0.2.3

- Internal improvements to init workflow

## 0.2.2

- With no API key, `agentcogs init` records the sample, and a later call inside `run()` is priced from the response and stored in that same file. `instrument()` does not write a row. Enforcement stays off.
- On the self-hosted API, a duplicate settles the customer already stored on the run. A retry that names another tenant does not add a second charge.
- `./scripts/accounting_bench.sh` posted 10,000 unique runs across five seeds. The ledger total was $3.239922 and the overshoot was 0. A naive spent-so-far add charged $0.648 extra. The chart and the recovery times are in `docs/accounting-bench.md`.

## 0.2.1

- A live OpenAI or Anthropic call inside `run()` is priced from the usage on the response. Cached tokens and cache writes are part of that bill. The server stores it.
- Chat completions report prompt tokens. A stream has to be read inside the block before that usage exists.

## 0.2.0

- A run can carry per-call token lanes. The server prices them in integer micro-USD and splits a nested cache write across the calls that used it. The same run with a different bill is rejected.
- Budget enforcement stays off until a workspace turns it on. A would-be block is recorded and the request continues.
- `agentcogs init` creates a local ledger, prices one sample call, and serves it on this machine. No Docker and no model call.
- The sample dashboard keeps dollar ticks inside the chart, phone date labels apart, and a public login with no email code.

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
