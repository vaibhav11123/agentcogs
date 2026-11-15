# AgentCOGS quickstart

Look at the sample, then self-host a workspace and post one cost.

## 1. Look at the sample

Open [agentcogs.vercel.app](https://agentcogs.vercel.app) and choose **Open Patternstack**. Vellum Research is the thin account. Nothing to type. That sample does not receive your agent. A hosted API is not serving.

## 2. Run it

```bash
git clone https://github.com/vaibhav11123/agentcogs.git
cd agentcogs
cp .env.selfhost.example .env
docker compose up -d --build
```

Open http://localhost:3000 and choose **Create my workspace**. No email. The next screen shows the install command with your API key and workspace id filled in.

## 3. Install

The package is not on PyPI yet.

```bash
pip install "agentcogs @ git+https://github.com/vaibhav11123/agentcogs.git"
```

From this repo, while you are changing the SDK:

```bash
pip install -e ".[dev]"
```

## 4. Verify connection

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

## 5. Attribute cost to a tenant

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

## 6. Run the hello script

```bash
export OPENAI_API_KEY='...'   # or ANTHROPIC_API_KEY (optional — zero-cost ingest test without either)
export AGENTCOGS_TEST_TENANT='vellum_research'   # optional, default hello_tenant
python3 examples/hello_agentcogs.py
```

The script calls `ping()`, runs one `run()`, and prints `wait_for_ingest()` status.

## 7. Confirm in the dashboard

Open **Customers**. The new row has cost and no fee. Type the monthly fee on that row. Margin is the fee minus the cost.

The in-app setup guide (`/onboarding`) polls until the first event arrives.

## Local full stack

The self-host commands in step 2 are the install. `./tools/seed_demo.sh` fills a demo company for screenshots. It is a separate workspace from the one **Create my workspace** makes.

## CLI

```bash
python -m agentcogs outbox status   # pending / failed ingests
```

Call `agentcogs.shutdown()` (or rely on process exit) to flush the ingest outbox in long-running apps.

## Next

- [Customer ID mapping](concepts/customer-id.md)
- [Troubleshooting](troubleshooting.md)
- [All docs](README.md)
