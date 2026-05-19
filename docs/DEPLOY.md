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

**Project settings**

- Root directory: `dashboard`
- Framework: Vite
- Build: `npm run build`
- Output: `dist`

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

1. Open https://agentcogs.vercel.app (or https://app.agentcogs.dev once DNS is set) → request magic link.
2. Settings → copy API key + workspace id.
3. Local:

```bash
pip install agentcogs
export AGENTCOGS_API_KEY='acg_live_...'
export AGENTCOGS_WORKSPACE_ID='...'
python3 examples/hello_agentcogs.py
```

4. Refresh dashboard — customer row appears.

---

## 5. Optional: GitHub Actions

Add repo secrets `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, then use workflow_dispatch in [.github/workflows/deploy-production.yml](../.github/workflows/deploy-production.yml).

---

## Self-host

Same stack locally: [backend/README.md](../backend/README.md), [dashboard/README.md](../dashboard/README.md), or `./tools/seed_demo.sh && ./tools/start_demo.sh` for a full local stack.
