# AgentCOGS documentation

## SDK integration (start here)

| Doc | Audience |
|-----|----------|
| [quickstart.md](quickstart.md) | First event in ~10 min (`ping()` → `set_customer` → `run()`) |
| [concepts/customer-id.md](concepts/customer-id.md) | Tenant mapping and rules |
| [troubleshooting.md](troubleshooting.md) | Empty dashboard, config errors, outbox |
| [integrations/fastapi.md](integrations/fastapi.md) | `AgentCOGSMiddleware` |
| [integrations/langgraph.md](integrations/langgraph.md) | `agentcogs_run()` helper |
| [integrations/customer-import.md](integrations/customer-import.md) | Pre-seed customers (optional) |

**Canonical script:** `examples/hello_agentcogs.py` (repo root).

## Demo paths (pick one)

| Path | Command | Needs |
|------|---------|--------|
| **Production SDK** | `python3 examples/hello_agentcogs.py` | Dashboard API key + LLM key (optional) |
| **Local full stack** | `./tools/seed_demo.sh` → `./tools/start_demo.sh` | Docker |
| **Live ingest on demo stack** | `python3 scripts/run_live_pipeline.py` | `seed_demo.sh` + `ANTHROPIC_API_KEY` |
| **Sales call (no backend)** | `python3 prototype/demo.py` | Nothing — prints mock JSON |
| **Shekel-only LLM smoke** | `python3 prototype.py` | `ANTHROPIC_API_KEY` — no AgentCOGS ingest |

Do not use `prototype/demo.py` to verify dashboard ingest; use `hello_agentcogs.py` or `run_live_pipeline.py`.

## Internal

- [SDK_CUSTOMER_JOURNEY_PLAN.md](SDK_CUSTOMER_JOURNEY_PLAN.md) — implementation plan (May 2026)
- [DEMO_CALL_SCRIPT.md](DEMO_CALL_SCRIPT.md) — 30-minute validation call script
- [launch/](launch/) — launch copy
