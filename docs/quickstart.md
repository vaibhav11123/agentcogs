# AgentCOGS quickstart

Look at the sample, then self-host a workspace and post one cost.

## 1. Look at the sample

Open [agentcogs.vercel.app](https://agentcogs.vercel.app) and choose **Open Patternstack**. Vellum Research is the thin account. Nothing to type. A hosted API is not serving, and the sample is a snapshot in the dashboard.

## 2. Self-host and install

```bash
cp .env.selfhost.example .env
docker compose up -d --build
```

Open http://localhost:3000 and choose **Create my workspace**. The next screen shows the install command with your key. The package is not on PyPI yet:

```bash
pip install "agentcogs @ git+https://github.com/vaibhav11123/agentcogs.git"
```

From a clone of this repo, while you are changing the SDK:

```bash
pip install -e ".[dev]"
```

## 3. Verify connection

```bash
export AGENTCOGS_API_KEY='acg_live_...'
export AGENTCOGS_WORKSPACE_ID='your-uuid'
export AGENTCOGS_ENDPOINT='http://localhost:8000'   # the API you are running
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
export AGENTCOGS_TEST_TENANT='vellum_research'   # optional, default hello_tenant
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

This seeds a demo workspace in Docker. It is separate from the self-host steps above.

## CLI

```bash
python -m agentcogs outbox status   # pending / failed ingests
```

Call `agentcogs.shutdown()` (or rely on process exit) to flush the ingest outbox in long-running apps.

## Next

- [Customer ID mapping](concepts/customer-id.md)
- [Troubleshooting](troubleshooting.md)
- [All docs](README.md)
