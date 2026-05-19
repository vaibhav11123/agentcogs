# Customer ID mapping

`customer_id` is the **billing tenant** for a block of LLM work. AgentCOGS does not discover tenants automatically — you provide an id your app already uses.

## Recommended pattern

```python
# Once per request (e.g. FastAPI dependency or middleware)
agentcogs.set_customer(request.state.tenant_id)

with agentcogs.run(workflow_id="research"):
    return graph.invoke(state)
```

## Mapping table

| Your system | Use as `customer_id` |
|-------------|----------------------|
| `tenants.id` / `org_id` | Same string |
| Clerk / Auth0 organization | `org_id` from JWT |
| Stripe subscription | Your tenant id (store `cus_*` in dashboard `stripe_customer_id`) |

## Rules

1. **One tenant per `run()`** — wrap one user request or job, not each LangGraph node.
2. **Stable ids** — changing ids creates duplicate dashboard rows.
3. **Lazy create** — first ingest upserts the customer row.
4. **Revenue & margin** — set `monthly_revenue_usd` in the dashboard (or import); the SDK only sends cost.

## Workers & async

```python
def process_job(job):
    agentcogs.set_customer(job.tenant_id)
    with agentcogs.run(workflow_id=job.workflow):
        ...
    agentcogs.set_customer(None)
```

## Pre-seed customers (optional)

`POST /v1/customers/import` can create rows before first LLM event (names, revenue, budgets). Attribution still requires `run()` / ingest. See [customer-import.md](../integrations/customer-import.md).

## Related

- [Quickstart](../quickstart.md)
- [FastAPI](../integrations/fastapi.md) · [LangGraph](../integrations/langgraph.md)
