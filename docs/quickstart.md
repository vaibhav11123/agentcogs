# AgentCOGS quickstart

Get your first per-customer cost event into the dashboard in about 10 minutes.

## 1. Sign up and copy credentials

1. Log in at the [dashboard](https://agentcogs.vercel.app) (magic link).
2. Complete **Connect the SDK** (`/onboarding`) or open **Settings**.
3. Copy **API key** and **workspace id**.

## 2. Install

<!-- verify -->
```bash
pip install agentcogs
```

From this monorepo:

```bash
pip install -e ".[dev]"
```

## 3. Verify connection

```bash
export AGENTCOGS_API_KEY='acg_live_...'
export AGENTCOGS_WORKSPACE_ID='your-uuid'
export AGENTCOGS_ENDPOINT='http://localhost:8000'   # hosted: https://agentcogs-api-production.up.railway.app
```

```python
import agentcogs

agentcogs.init()  # reads AGENTCOGS_* env vars
# or: agentcogs.init(api_key="...", workspace_id="...", endpoint="...")

print(agentcogs.ping())  # PingResult(ok=True, ...)
```

`ping()` checks API key, workspace, and reachability. Fix `ConfigurationError` or `PingError` before wiring agents.

## 4. Attribute cost to a tenant

**Recommended:** set tenant once per HTTP request or background job, then wrap agent code:

```python
agentcogs.set_customer(tenant_id)  # same id as your tenants table

with agentcogs.run(workflow_id="support_bot"):
    result = my_agent.invoke(...)
```

**Explicit** (still supported):

```python
with agentcogs.run(customer_id=tenant_id, workflow_id="support_bot"):
    result = my_agent.invoke(...)
```

Customers appear in the dashboard on **first ingest** for each `customer_id`. See [customer-id.md](concepts/customer-id.md).

### Framework helpers

- [FastAPI middleware](integrations/fastapi.md) — `AgentCOGSMiddleware` sets context from `request.state`
- [LangGraph](integrations/langgraph.md) — `agentcogs_run(config, workflow_id=...)`

## 5. Run the hello script

```bash
export OPENAI_API_KEY='...'   # or ANTHROPIC_API_KEY (optional — zero-cost ingest test without either)
export AGENTCOGS_TEST_TENANT='acme_dev'   # optional, default hello_tenant
python3 examples/hello_agentcogs.py
```

The script calls `ping()`, runs one `run()`, and prints `wait_for_ingest()` status.

## 6. Confirm in the dashboard

Open **Customers** — you should see your test tenant and the run.

The in-app setup guide (`/onboarding`) polls until the first event arrives.

## Local full stack (optional)

For demo personas, leaderboard screenshots, and sales calls with a live UI:

```bash
./tools/seed_demo.sh
./tools/start_demo.sh
# http://localhost:5173/demo

# Real SDK ingest into that workspace:
export ANTHROPIC_API_KEY='...'
python3 scripts/run_live_pipeline.py
```

This is separate from the production quickstart above (hosted API + your workspace keys).

## CLI

```bash
python -m agentcogs outbox status   # pending / failed ingests
```

Call `agentcogs.shutdown()` (or rely on process exit) to flush the ingest outbox in long-running apps.

## Next

- [Customer ID mapping](concepts/customer-id.md)
- [Troubleshooting](troubleshooting.md)
- [All docs](README.md)
