# Deploy AgentCOGS (production)

**Targets:** `api.agentcogs.dev` (Railway) · `app.agentcogs.dev` (Vercel)

DNS must point to each provider before magic-link cookies work on `.agentcogs.dev`.

---

## 1. Railway — API + Postgres + Redis

### API token (pick one)

| Type | Where to create | `.env.deploy.local` | CLI / curl header |
|------|-----------------|---------------------|-------------------|
| **Account** (recommended) | Account → **Settings → Tokens** | `RAILWAY_API_TOKEN=` | `Authorization: Bearer …` |
| **Workspace** | Same page, pick workspace | `RAILWAY_API_TOKEN=` | `Authorization: Bearer …` |
| **Project** | Project → **Settings → Tokens** | `RAILWAY_TOKEN=` | `Project-Access-Token: …` (GraphQL) |

The **project UUID** in the dashboard URL is **not** a token. Masked values (`****-f339`) cannot be copied again — create a **New Token** and save the full secret once.

Test account token:

```bash
curl -sS -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { me { name email } }"}'
```

### Create / link project

```bash
npm i -g @railway/cli
cd backend
# with RAILWAY_API_TOKEN set:
railway init --name agentcogs-api
```

### Add data stores

In [Railway dashboard](https://railway.com) → project → **+ New**:

- **PostgreSQL** → copy `DATABASE_URL` into the API service variables
- **Redis** → copy `REDIS_URL`

### API service variables

Set on the **backend** service (root directory: `backend`, builder: Dockerfile — see `railway.toml`):

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` or pooler URL |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `https://app.agentcogs.dev` |
| `APP_BASE_URL` | `https://app.agentcogs.dev` |
| `RESEND_API_KEY` | Resend API key (magic-link email) |
| `ALERT_FROM_EMAIL` | `alerts@agentcogs.dev` (verified domain in Resend) |
| `STRIPE_API_KEY` | optional |
| `STRIPE_WEBHOOK_SECRET` | optional |

Migrations run on every deploy (`python scripts/migrate.py` in `railway.toml`).

### Custom domain

Railway → API service → **Settings → Networking → Custom Domain** → `api.agentcogs.dev`

At your DNS host:

| Type | Name | Value |
|------|------|--------|
| CNAME | `api` | Railway-provided hostname |

Verify:

```bash
curl -sS https://api.agentcogs.dev/health
# {"status":"ok"}
curl -sS https://api.agentcogs.dev/health/ready
# postgres + redis ok
```

---

## 2. Vercel — dashboard

```bash
npm i -g vercel
vercel login
cd dashboard
vercel link
```

**Project settings (GitHub deploys)**

The repo root includes [`vercel.json`](../vercel.json) so monorepo builds run in `dashboard/` (`npm run build`, not bare `vite build`).

If you linked the project manually, set **Root Directory** = `dashboard`, Framework = Vite, Output = `dist`.

**Environment (Production)**

| Variable | Value |
|----------|--------|
| `VITE_API_URL` | `https://api.agentcogs.dev` |

```bash
vercel --prod
```

### Custom domain

Vercel → Project → **Domains** → `app.agentcogs.dev`

DNS:

| Type | Name | Value |
|------|------|--------|
| CNAME | `app` | `cname.vercel-dns.com` (or value Vercel shows) |

Optional apex `agentcogs.dev` → redirect to `app.agentcogs.dev` in Vercel.

---

## 3. Resend + cookies

1. Add domain `agentcogs.dev` in [Resend](https://resend.com) and set DNS records.
2. Use `alerts@agentcogs.dev` (or `hello@`) as `ALERT_FROM_EMAIL`.
3. Production auth sets cookie `domain=.agentcogs.dev` — both `app` and `api` must be on that domain (not `*.railway.app` for real users).

---

## 4. Smoke test

A hosted API and magic-link email are not the path a new person uses. Use the self-host steps below. Magic link needs a live API, a verified email domain, and `RESEND_API_KEY`.

---

## 5. Optional: GitHub Actions

Add repo secrets `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, then use workflow_dispatch in [.github/workflows/deploy-production.yml](../.github/workflows/deploy-production.yml).

---

## Self-host

One-command full stack at the repo root (Postgres, Redis, migrations, API, dashboard):

```bash
cp .env.selfhost.example .env
docker compose up -d --build
```

1. Open http://localhost:3000 and choose **Create my workspace**. No email. The API key is on the next screen, inside the install command.
2. Copy that command. It installs from git, because the package is not on PyPI yet, and it already contains the key, the workspace id, and `http://localhost:8000`.
3. Run one agent call, open the customer, and type the monthly fee. Margin is that fee minus the cost.

The setup endpoint that creates the workspace is open on a self-hosted process. Keep port 8000 on localhost. Slack buttons open `http://localhost:3000`. Set `APP_BASE_URL` if the dashboard is served somewhere else.

Contributor install from this repo, if you are changing the SDK:

```bash
pip install -e ".[dev]"
export AGENTCOGS_ENDPOINT='http://localhost:8000'
python3 examples/hello_agentcogs.py
```

Headless check: `./scripts/selfhost_smoke.sh` (Docker only).

For backend-only dev (no dashboard container): [backend/README.md](../backend/README.md) and `backend/docker-compose.yml`.
