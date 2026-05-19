# AgentCOGS — litellm-docs PR draft

Submit this file to [BerriAI/litellm-docs](https://github.com/BerriAI/litellm-docs) (not the main litellm repo). Path: `docs/observability/agentcogs.md` (confirm path in that repo).

---

# AgentCOGS - Per-customer margin

[AgentCOGS](https://github.com/vaibhav11123/agentcogs) tracks per-customer LLM cost and gross margin for B2B SaaS (cost + revenue), alongside your existing proxy and observability stack.

## Quick Start

```python
import os
import litellm

os.environ["AGENTCOGS_API_KEY"] = ""
os.environ["AGENTCOGS_WORKSPACE_ID"] = ""
os.environ["AGENTCOGS_ENDPOINT"] = "https://api.agentcogs.dev"  # optional

litellm.success_callback = ["agentcogs"]

response = litellm.completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hi"}],
    user="your_customer_id",
    metadata={"agentcogs_workflow_id": "support_bot"},
)
```

Proxy:

```yaml
litellm_settings:
  callbacks: ["agentcogs"]
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AGENTCOGS_API_KEY` | Yes | Workspace API key |
| `AGENTCOGS_WORKSPACE_ID` | Yes | Workspace UUID |
| `AGENTCOGS_ENDPOINT` | No | API base (default `https://api.agentcogs.dev`) |
| `AGENTCOGS_CHARGE_BY` | No | Proxy attribution: `end_user_id` (default), `user_id`, `team_id` — same as [Lago](./lago.md) |

## Tenant attribution

**Proxy:** Uses `AGENTCOGS_CHARGE_BY` (default `end_user_id` from request `user` in proxy body). Client `metadata.agentcogs_customer_id` is not trusted on proxy traffic.

**SDK / direct:** `user=` or `metadata.agentcogs_customer_id`.

Completions without a resolvable customer id are skipped (non-blocking).

## Learn more

- [AgentCOGS quickstart](https://github.com/vaibhav11123/agentcogs/blob/main/docs/quickstart.md)
- [User-landed callback](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/litellm.md)
