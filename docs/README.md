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

## Demo paths

README shows two entry paths (sales mock vs real ingest). Full matrix, terminal captures, and UI gallery: **[demo-paths.md](demo-paths.md)**.
