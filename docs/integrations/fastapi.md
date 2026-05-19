# FastAPI integration

Set tenant context once per request via middleware, then use `agentcogs.run(workflow_id=...)` without repeating `customer_id`.

Requires `agentcogs.init()` at app startup (or env vars).

## Middleware

```python
import agentcogs
from fastapi import FastAPI
from agentcogs.integrations.fastapi import AgentCOGSMiddleware

agentcogs.init()  # or rely on AGENTCOGS_* env

app = FastAPI()
app.add_middleware(
    AgentCOGSMiddleware,
    customer_id=lambda req: getattr(req.state, "tenant_id", None),
    workflow_id=lambda req: getattr(req.state, "workflow_id", None),  # optional
)


@app.post("/agents/run")
async def run_agent():
    with agentcogs.run(workflow_id="support"):
        # LLM calls here
        ...
```

Register auth middleware **before** `AgentCOGSMiddleware` so `request.state.tenant_id` is set. Health paths `/health` and `/health/ready` are excluded by default.

## Async handlers

```python
import asyncio

with agentcogs.run(workflow_id="support"):
    result = await asyncio.to_thread(graph.invoke, state)
```
