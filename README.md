# AgentCOGS Monorepo

Three production repos in one workspace (split to separate GitHub repos when ready):

| Path | Repo | Description |
|------|------|-------------|
| `/` | [agentcogs](https://github.com/vaibhav11123/agentcogs) | Python SDK — `pip install agentcogs` |
| `backend/` | agentcogs-backend | FastAPI ingest + dashboard API |
| `dashboard/` | agentcogs-dashboard | React dashboard (Vercel) |

GitHub: [docs/GITHUB.md](docs/GITHUB.md) — CI, branch protection, org transfer.

## Quick start

**SDK (production):** [docs/quickstart.md](docs/quickstart.md) — sign up → `pip install agentcogs` → `examples/hello_agentcogs.py` → first row in dashboard (~10 min).

```bash
export AGENTCOGS_API_KEY='...' AGENTCOGS_WORKSPACE_ID='...'
export AGENTCOGS_ENDPOINT='http://localhost:8000'   # local API only
python3 examples/hello_agentcogs.py
```

**Docs index:** [docs/README.md](docs/README.md)

```bash
# Full E2E (Docker + jq)
./test_e2e.sh

# SDK dev
pip install -e ".[dev]"
pytest

# Local dashboard + seeded personas
./tools/seed_demo.sh && ./tools/start_demo.sh
# http://localhost:5173/demo

# Live SDK ingest against local demo API (after seed)
export ANTHROPIC_API_KEY='...'
python3 scripts/run_live_pipeline.py

# Sales call — mock JSON, no backend
python3 prototype/demo.py

# Shekel + LLM only (no AgentCOGS ingest)
python3 prototype.py
```

Launch copy: `docs/launch/`

See each subdirectory README for deploy instructions.
