# AgentCOGS Backend

FastAPI service for cost event ingest, budget checks, dashboard API, anomaly alerts, and Stripe sync.

## Setup

```bash
cp .env.example .env   # fill DATABASE_URL, REDIS_URL, JWT_SECRET
psql $DATABASE_URL -f migrations/versions/001_init.sql
pip install -e .
uvicorn app.main:app --reload
```

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres (Supabase pooler port 6543) |
| `REDIS_URL` | Upstash Redis URL |
| `JWT_SECRET` | Dashboard session signing |
| `STRIPE_API_KEY` | Stripe billing + Connect |
| `RESEND_API_KEY` | Email alerts |

## Deploy

Railway with `railway.toml`. Cron job: `python -m app.jobs.nightly_stripe_sync` at 02:00 UTC.
