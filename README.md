# AgentCOGS Monorepo

Three production repos in one workspace (split to separate GitHub repos when ready):

| Path | Repo | Description |
|------|------|-------------|
| `/` | [agentcogs](https://github.com/vaibhav11123/agentcogs) | Python SDK — `pip install agentcogs` |
| `backend/` | agentcogs-backend | FastAPI ingest + dashboard API |
| `dashboard/` | agentcogs-dashboard | React dashboard (Vercel) |

GitHub: [docs/GITHUB.md](docs/GITHUB.md) — CI, branch protection, org transfer.

## Quick start

```bash
# Full E2E (14 tests, needs Docker + jq)
./test_e2e.sh

# SDK
pip install -e ".[dev]"
pytest

# Backend
cd backend && cp .env.example .env
docker compose up -d
docker compose exec -T postgres psql -U postgres -d agentcogs < migrations/versions/001_init.sql
uvicorn app.main:app --reload

# Dashboard
cd dashboard && npm install && npm run dev

# Week 0 demo call
python prototype.py   # needs OPENAI_API_KEY
```

Launch copy: `docs/launch/`

See each subdirectory README for deploy instructions.
