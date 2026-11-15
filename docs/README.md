# AgentCOGS documentation

AgentCOGS is customer-level AI unit economics for a B2B product: each LLM call attributed to the customer who caused it, set against that customer's monthly fee. AI margin is `(monthly fee − attributed AI cost) / monthly fee`. It is not total customer profitability.

**Open source:** [OPEN_SOURCE.md](OPEN_SOURCE.md) · **Contributing:** [../CONTRIBUTING.md](../CONTRIBUTING.md)

## Deploy

Production (Railway + Vercel + DNS): **[DEPLOY.md](DEPLOY.md)**

## SDK integration (start here)

| Doc | Audience |
|-----|----------|
| [quickstart.md](quickstart.md) | First event. Path A is a recorded cost. Path B is a real model call |
| [cost-methodology.md](cost-methodology.md) | Fee minus attributed AI cost, and what that leaves out |
| [budget-semantics.md](budget-semantics.md) | The pre-call budget check, and what it does not stop |
| [concepts/customer-id.md](concepts/customer-id.md) | Tenant mapping and rules |
| [troubleshooting.md](troubleshooting.md) | Empty dashboard, config errors, outbox |
| [integrations/fastapi.md](integrations/fastapi.md) | `AgentCOGSMiddleware` |
| [integrations/langgraph.md](integrations/langgraph.md) | `agentcogs_run()` helper |
| [integrations/litellm.md](integrations/litellm.md) | Optional LiteLLM proxy callback |
| [integrations/customer-import.md](integrations/customer-import.md) | Pre-seed customers (optional) |
| [integrations/slack.md](integrations/slack.md) | Cost spike alerts via Incoming Webhook |

**Canonical script:** `examples/hello_agentcogs.py` (repo root).

## Local development

Scripts, smoke tests, and terminal captures: **[demo-paths.md](demo-paths.md)** (contributor reference).
