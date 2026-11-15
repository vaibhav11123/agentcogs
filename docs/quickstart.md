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

```bash
pip install agentcogs
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

## 5. Two ways to post a cost

Path A and Path B both need the key, workspace, and endpoint from step 4. They are not the same proof.

### Path A — a recorded cost, no model call

`examples/one_run.py` posts one event with `total_usd` of 0.84 for `vellum_research`. It does not call OpenAI or Anthropic. Use it to see a row when you have no model key. Do not treat that 0.84 as a measured model bill.

```bash
python examples/one_run.py
```

### Path B — a real model call, or a zero-cost run

`examples/hello_agentcogs.py` calls `ping()`, sets a customer, and wraps one block. If `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set, shekel reads that call's token usage and the SDK posts that cost when the block exits. With neither key, the same block posts a zero-cost run so you can see the row.

```bash
python examples/hello_agentcogs.py
```

The same shape in your own code:

```python
import os
from openai import OpenAI
import agentcogs

agentcogs.set_customer("acme")  # your tenant id, once per request

with agentcogs.run(workflow_id="support") as ctx:
    if os.environ.get("OPENAI_API_KEY"):
        OpenAI().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hi in one word."}],
            max_tokens=5,
        )

print(ctx.wait_for_ingest().accepted, ctx.run_id)
```

`OpenAI().chat.completions.create` is the call you make. The SDK does not define an agent for you, and it does not call a model by itself. If the block makes no instrumented call, the posted cost is zero.

You can also pass the tenant into `run(customer_id=..., workflow_id=...)` instead of `set_customer()`.

Then open that customer and type the monthly fee. AI margin is `(fee − attributed AI cost) / fee`. It is not total customer profitability, and it is not accounting gross margin. The full rules are in [cost-methodology.md](cost-methodology.md). The budget check is separate: [budget-semantics.md](budget-semantics.md).

Customers appear in the dashboard on **first ingest** for each `customer_id`. See [customer-id.md](concepts/customer-id.md).

### Framework helpers

- [FastAPI middleware](integrations/fastapi.md) — `AgentCOGSMiddleware` sets context from `request.state`
- [LangGraph](integrations/langgraph.md) — `agentcogs_run(config, workflow_id=...)`

## 6. Optional tenant name for Path B

```bash
export AGENTCOGS_TEST_TENANT='vellum_research'   # optional, default hello_tenant
```

Path B prints `wait_for_ingest()` and the tenant it used.

## 7. Confirm in the dashboard

Open **Customers**. The new row has cost and no fee. Type the monthly fee on that row. Margin is the fee minus the cost.

The in-app setup guide (`/onboarding`) polls until the first event arrives.

## Local full stack

The self-host commands in step 2 are the install. `./tools/seed_demo.sh` fills a demo company for screenshots. It is a separate workspace from the one **Create my workspace** makes.

## CLI

```bash
python -m agentcogs outbox status   # pending / failed ingests
```

Set `POSTHOG_PROJECT_API_KEY` to send that command name, the package version, and success or failure to PostHog. `POSTHOG_HOST` defaults to `https://us.i.posthog.com`. Leave the key unset and the command does not call PostHog. The event leaves out prompts, customer names, API keys, and amounts.

Call `agentcogs.shutdown()` (or rely on process exit) to flush the ingest outbox in long-running apps.

## Next

- [Customer ID mapping](concepts/customer-id.md)
- [Troubleshooting](troubleshooting.md)
- [All docs](README.md)
