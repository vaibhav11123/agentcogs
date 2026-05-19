# Open source posture

AgentCOGS is **MIT-licensed** and **self-host first**. The monorepo contains the SDK, backend API, and dashboard — not only the PyPI package.

## What is open

| Area | License / notes |
|------|-----------------|
| Python SDK (`src/agentcogs/`) | MIT — `pip install agentcogs` |
| Backend + dashboard | MIT — run locally or deploy yourself |
| Docs (`docs/`) | Same repo; GTM playbooks are public strategy notes |

## What is not in this repo

- Hosted `api.agentcogs.dev` / `app.agentcogs.dev` (may be offline until we deploy)
- Production secrets, customer data, or `tools/.demo_env` (gitignored)

## Before you fork or publish

```bash
chmod +x scripts/audit_before_public.sh
./scripts/audit_before_public.sh
```

Review `docs/internal/` — planning notes only, no credentials, but may reference in-flight PRs.

## Hosted product vs OSS

| Path | Best for |
|------|----------|
| **Self-host** | Full control, air-gapped, custom billing |
| **`pip install agentcogs` + your API** | SDK only against your backend |
| **Hosted AgentCOGS** (future) | Fastest onboarding when live |

We ship integrations (LiteLLM, Langfuse discussions, etc.) in the open so users are not blocked on our SaaS uptime.

## Making this repo public (maintainer checklist)

1. `./scripts/audit_before_public.sh`
2. `pytest` + `cd dashboard && npm run build`
3. Confirm `tools/.demo_env` and `.env` are not tracked
4. `gh repo edit vaibhav11123/agentcogs --visibility public --accept-visibility-change-consequences`
5. Enable branch protection on `main` (see [GITHUB.md](GITHUB.md))
