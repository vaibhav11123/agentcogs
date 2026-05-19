# AgentCOGS

**Open source (MIT)** — per-customer LLM cost attribution for AI agents. Self-host the full stack or use the SDK against your own API.

| Component | Path | Description |
|-----------|------|-------------|
| **SDK** | `src/agentcogs/` | `pip install agentcogs` — wrap runs, set `customer_id`, ingest cost events |
| **Backend** | `backend/` | FastAPI ingest + dashboard API |
| **Dashboard** | `dashboard/` | React UI for spend by customer |

**License:** [MIT](LICENSE) · **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) · **Security:** [SECURITY.md](SECURITY.md) · **OSS notes:** [docs/OPEN_SOURCE.md](docs/OPEN_SOURCE.md)

> **Hosted product:** `api.agentcogs.dev` / `app.agentcogs.dev` may not be live yet. Use [self-host](#self-host) or local demo below.

## Quick start (SDK)

[docs/quickstart.md](docs/quickstart.md) — sign up on your instance → `pip install agentcogs` → `examples/hello_agentcogs.py`.

```bash
export AGENTCOGS_API_KEY='...' AGENTCOGS_WORKSPACE_ID='...'
export AGENTCOGS_ENDPOINT='http://localhost:8000'   # your API
python3 examples/hello_agentcogs.py
```

**Docs index:** [docs/README.md](docs/README.md)

## Self-host

```bash
# Full E2E (Docker + jq)
./test_e2e.sh

# Backend
cd backend && cp .env.example .env   # edit DATABASE_URL, REDIS_URL, JWT_SECRET
# see backend/README.md

# Dashboard
cd dashboard && cp .env.example .env
npm ci && npm run dev

# Seeded local demo (personas + UI)
./tools/seed_demo.sh && ./tools/start_demo.sh
# http://localhost:5173/demo
```

```bash
# SDK development
pip install -e ".[dev]"
pytest

# Live SDK ingest against local demo API (after seed)
export ANTHROPIC_API_KEY='...'
python3 scripts/run_live_pipeline.py
```

## Repo layout

| Path | What |
|------|------|
| `src/agentcogs/` | Python SDK |
| `backend/` | FastAPI API |
| `dashboard/` | React UI |
| `tests/` | SDK pytest suite |
| `examples/` | Canonical SDK scripts |
| `scripts/smoke/` | Manual smoke scripts |
| `prototype/` | Sales mock + Shekel-only demo (no ingest) |
| `tools/` | Local demo stack, seed, generators |
| `docs/` | User + integration docs |
| `docs/internal/` | Maintainer notes (debt register, test logs) |

## Integrations

- [LiteLLM](docs/integrations/litellm.md) — proxy callback (upstream PR in progress)
- [FastAPI](docs/integrations/fastapi.md), [LangGraph](docs/integrations/langgraph.md), [Slack alerts](docs/integrations/slack.md)

## GitHub

[docs/GITHUB.md](docs/GITHUB.md) — CI, branch protection, org transfer.
