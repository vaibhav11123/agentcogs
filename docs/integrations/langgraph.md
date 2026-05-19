# LangGraph integration

Pass `tenant_id` in LangGraph `configurable` and wrap `invoke`:

```python
import agentcogs
from agentcogs.integrations.langgraph import agentcogs_run

config = {
    "configurable": {
        "tenant_id": request.state.tenant_id,
        "thread_id": "...",
    }
}

with agentcogs_run(config, workflow_id="research_agent") as ctx:
    result = graph.invoke(state, config)

print(ctx.run_id)
```

Or manually:

```python
agentcogs.set_customer(config["configurable"]["tenant_id"])
with agentcogs.run(workflow_id="research_agent"):
    result = graph.invoke(state, config)
```

`node_costs` in the dashboard requires per-node Shekel hooks (planned). Cost and margin at the customer level work with the snippet above.

See also [customer-id.md](../concepts/customer-id.md) and [quickstart.md](../quickstart.md).
