# AgentCOGS documentation

**Open source:** [OPEN_SOURCE.md](OPEN_SOURCE.md) · **Contributing:** [../CONTRIBUTING.md](../CONTRIBUTING.md)

## SDK integration (start here)

| Doc | Audience |
|-----|----------|
| [quickstart.md](quickstart.md) | First event in ~10 min (`ping()` → `set_customer` → `run()`) |
| [concepts/customer-id.md](concepts/customer-id.md) | Tenant mapping and rules |
| [troubleshooting.md](troubleshooting.md) | Empty dashboard, config errors, outbox |
| [integrations/fastapi.md](integrations/fastapi.md) | `AgentCOGSMiddleware` |
| [integrations/langgraph.md](integrations/langgraph.md) | `agentcogs_run()` helper |
| [integrations/litellm.md](integrations/litellm.md) | Optional LiteLLM proxy callback |
| [integrations/customer-import.md](integrations/customer-import.md) | Pre-seed customers (optional) |
| [integrations/slack.md](integrations/slack.md) | Cost spike alerts via Incoming Webhook |

**Canonical script:** `examples/hello_agentcogs.py` (repo root).

## Demo paths (pick one)

| Path | Command | Needs |
|------|---------|--------|
| **Production SDK** | `python3 examples/hello_agentcogs.py` | Dashboard API key + LLM key (optional) |
| **Local full stack** | `./tools/seed_demo.sh` → `./tools/start_demo.sh` | Docker |
| **Live ingest on demo stack** | `python3 scripts/run_live_pipeline.py` | `seed_demo.sh` + `ANTHROPIC_API_KEY` |
| **Sales call (no backend)** | `python3 prototype/demo.py` | Nothing — prints mock JSON |
| **Shekel-only LLM smoke** | `python3 prototype/shekel_smoke.py` | `ANTHROPIC_API_KEY` — no AgentCOGS ingest |

Do not use `prototype/demo.py` to verify dashboard ingest; use `hello_agentcogs.py` or `run_live_pipeline.py`.
