# Contributing

Thanks for helping improve AgentCOGS. This repo is **open source (MIT)** and **self-host first** — the hosted product at agentcogs.dev is optional and may lag the repo.

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
