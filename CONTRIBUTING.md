# Contributing

Thanks for helping improve AgentCOGS. This repo is **open source (MIT)**. The hosted product at [app.agentcogs.dev](https://app.agentcogs.dev) is deployed from `main`; self-host instructions are in [docs/DEPLOY.md](docs/DEPLOY.md).

## What to work on

- **SDK** (`src/agentcogs/`, `tests/`) — customer attribution, ingest, framework helpers
- **Backend** (`backend/`) — ingest API, dashboard API, alerts
- **Dashboard** (`dashboard/`) — React UI
- **Docs** (`docs/`) — quickstart, integrations, troubleshooting

## Development setup

```bash
# SDK
pip install -e ".[dev]"
pytest

# Full stack (Docker)
./test_e2e.sh

# Local demo UI
./tools/seed_demo.sh && ./tools/start_demo.sh
```

See [backend/README.md](backend/README.md) and [dashboard/README.md](dashboard/README.md) for service-specific setup.

## Git hooks (run once after clone)

```bash
./scripts/install-githooks.sh
```

- **commit-msg** — rejects `Co-authored-by: Cursor`, `Made with Cursor`, etc.
- **pre-commit** — blocks `.cursor/`, GTM/internal docs, `.env`, `tools/.demo_env`

In **Cursor → Settings → Agents → Attribution**, disable commit/PR attribution so the IDE does not inject `Co-authored-by: Cursor <cursoragent@cursor.com>`.

If **cursoragent** still appears on the repo sidebar after a history rewrite, GitHub’s contributor widget can lag behind the API (often hours). Push is clean when `./scripts/check_no_cursor_attribution.sh origin/main` passes and [contributors API](https://api.github.com/repos/vaibhav11123/agentcogs/contributors) lists only your account. To rewrite SHAs: `./scripts/rewrite_history_no_cursor.sh` then `git push --force-with-lease origin main`.

## Pull requests

1. Branch from `main`
2. Keep changes focused; match existing style
3. Add or update tests when behavior changes
4. Ensure CI passes: SDK Tests, Backend Tests, Dashboard Build
5. Open a PR with a short summary and test plan

## Integrations upstream

LiteLLM callback lives in [BerriAI/litellm](https://github.com/BerriAI/litellm) (see [docs/integrations/litellm.md](docs/integrations/litellm.md)). Docs for proxy env vars go in [BerriAI/litellm-docs](https://github.com/BerriAI/litellm-docs).

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
