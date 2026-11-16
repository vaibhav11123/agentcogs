# AgentCOGS

The unit economics platform for AI SaaS.

**Know which AI customers make you money, and which ones are eating your margins.**

AgentCOGS connects each customer's AI usage cost to the monthly fee, so a B2B company can see that contribution margin before the month ends.

**Which customer stops making money this month.** The blended total can look fine while one fee no longer covers the AI cost.

```bash
pip install agentcogs
```

Open-source Python SDK. Self-hosted dashboard. Customer-level AI margin.

The package is the SDK. The customer list is the dashboard, and you run it yourself. A hosted API is not serving. Demo: [agentcogs.vercel.app](https://agentcogs.vercel.app).

| | |
| --- | --- |
| Look at the sample | [agentcogs.vercel.app](https://agentcogs.vercel.app) → **Open Patternstack**. Fictional data, as of 14 Nov 2026. Nothing to type. |
| Run your own customers | Self-host, choose **Create my workspace**, then point the SDK at `http://localhost:8000`. |
| Hosted | Not serving. |

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/vaibhav11123/agentcogs/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/vaibhav11123/agentcogs/actions/workflows/ci.yml/badge.svg)](https://github.com/vaibhav11123/agentcogs/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentcogs.svg)](https://pypi.org/project/agentcogs/)

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/patternstack.gif" alt="Opening the fictional Patternstack sample. AI margin is 74.6%. Vellum Research is 29.0% so far and the month ends near −52.2%." width="840">

---

## What does the number mean?

AI margin is `(monthly fee − attributed AI cost) / monthly fee`. It is the contribution of the fee after attributed AI cost. It is not total customer profitability, and it is not accounting gross margin. The full rules are in [docs/cost-methodology.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/cost-methodology.md). People, infrastructure, support, payment processing, refunds, discounts, credits, and proration are outside it. Pace is a straight line from the cost so far. It does not forecast a change in behavior. The fee is the monthly amount on the account. You type it, or you pull that customer's Stripe subscription. The SDK does not invent it.

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/screenshots/patternstack-customers.png" alt="Patternstack customer list, fictional. AI margin 74.6%. Vellum Research is 29.0% and the month ends near −52.2%." width="880">

---

## Where does the cost come from?

The SDK does not call a model. Inside `agentcogs.run()`, shekel reads token usage from the OpenAI and Anthropic calls you make in that block. When the block exits, the SDK posts that cost. If the block makes no instrumented call, the posted cost is zero. If no customer is set, `run()` raises before the block.

```python
import os
from openai import OpenAI
import agentcogs

agentcogs.init()  # AGENTCOGS_API_KEY, AGENTCOGS_WORKSPACE_ID, AGENTCOGS_ENDPOINT
print(agentcogs.ping())
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

`python examples/hello_agentcogs.py` is that path. Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` and it makes one short call. With neither key, it posts a zero-cost run so you can see the row. Open that customer and type the monthly fee.

`python examples/one_run.py` posts one recorded cost of USD 0.84 for Vellum Research. It does not call a model.

`AGENTCOGS_ENDPOINT` defaults to `http://localhost:8000`.

---

## What does the fictional sample show?

Patternstack, as of 14 Nov 2026. Forty customers. The month so far looks healthy.

| | So far | If the calls continue |
| --- | ---: | ---: |
| AI cost | $39,613.25 | $84,885.54 |
| Fees | $155,918.00 | $155,918.00 |
| AI margin | 74.6% | 45.6% |

Vellum Research has spent USD 5,822.84 against a fee of USD 8,200: **29.0%** so far, 2,724 runs, and the largest node is `synthesize`. If that spend continues, the month ends near **−52.2%**. Pinnacle Claims is 35.0% so far and ends near −39.3%. The blended 74.6% does not show either of those.

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/screenshots/vellum-research.png" alt="Vellum Research customer detail. AI margin 29.0%, AI cost USD 5,822.84, fee USD 8,200, and the set_customer call that posts each run." width="880">

---

## How do you run your own customers?

From this repo:

```bash
cp .env.selfhost.example .env
docker compose up -d --build
```

Open http://localhost:3000 and choose **Create my workspace**. No email. The next screen has the install command with your key in it.

```bash
pip install agentcogs
```

Point `AGENTCOGS_ENDPOINT` at `http://localhost:8000` if you have not already. Send one call, open that customer, and type the monthly fee.

Full steps: [docs/quickstart.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/quickstart.md). Self-host notes: [docs/DEPLOY.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/DEPLOY.md).

The FastAPI middleware is a separate extra: `pip install "agentcogs[integrations]"`.

---

## Who is it for?

Founders and the engineers who run a B2B product that sells one agent to many companies, priced as a monthly fee, with the model bill arriving as a single invoice. Support, research, claims, intake, document pipelines.

The category is customer-level AI unit economics. The same product is per-customer LLM cost tracking, multi-tenant attribution, and a budget check before the next call. Observability, a gateway, and billing answer different questions.

| Tool | The question it answers |
| --- | --- |
| LLM observability | Why did this call fail, or cost this much? |
| An LLM gateway | How do we route and manage model requests? |
| Billing | How much should we charge the customer? |
| AgentCOGS | Does this customer's fee still cover their AI cost? |

| You already have | AgentCOGS adds |
| --- | --- |
| Langfuse or LangSmith | The fee next to the cost, and whether that fee still covers it |
| LiteLLM | A callback you register. LiteLLM does not ship it. The proxy stays |
| Stripe | The subscription as the fee, and an optional meter for usage you already attributed |
| The provider invoice | A customer list to set against that one number. It does not reconcile the invoice |

---

## What can you connect?

| | |
| --- | --- |
| [FastAPI](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/fastapi.md) | Set the tenant from the request. Needs `agentcogs[integrations]` |
| [LangGraph](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/langgraph.md) | Wrap the graph |
| [LiteLLM](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/litellm.md) | A callback you copy in. It posts after the proxy call |
| [Customer import](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/customer-import.md) | Load names and fees before the first run |
| [Slack](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/slack.md) | A spike opens that customer |
| Stripe | Pull subscription fees. Push a daily usage meter |

Terminal proof for the SDK, the outbox, and a live call: [docs/demo-paths.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/demo-paths.md).

---

## What does the budget check do?

Before the block, the SDK asks whether this customer is already over `monthly_budget_usd`. If they are, it raises `CustomerBudgetExceededError` and does not enter the block. Two calls already in flight can both pass that check. It is not an atomic reservation. A proxy callback records cost after the provider has already answered.

---

## What is tested, and what is not?

Tested in this repo: a duplicate `run_id` is accepted as a duplicate and is not stored twice; a failed ingest sits in a local outbox and is retried, including across a process restart of that queue; the budget check raises before the block when the customer is already over the cap.

Not a guarantee: two concurrent calls that both pass the pre-check, a match against the provider invoice, refunds, credits, discounts, or currency conversion. `ping()` checks that your key and endpoint answer. `python -m agentcogs outbox status` shows what has not been delivered yet. `agentcogs.init()` stars https://github.com/vaibhav11123/agentcogs when `gh` is already logged in. If `gh` is missing, logged out, or the star fails, setup continues.

---

## Repo

| Path | |
| --- | --- |
| `src/agentcogs/` | The SDK. Required dependencies are shekel (OpenAI and Anthropic extras) and httpx |
| `backend/` | Ingest, margin, pace, budgets |
| `dashboard/` | The customer list |
| `examples/hello_agentcogs.py` | Ping, one run, and `wait_for_ingest()` |
| `examples/one_run.py` | One recorded cost of USD 0.84, no model call |
| `docs/cost-methodology.md` | What the fee and the cost include |
| `docs/` | [Index](https://github.com/vaibhav11123/agentcogs/blob/main/docs/README.md) |

- Sample: https://agentcogs.vercel.app
- Package: https://pypi.org/project/agentcogs/
- Source: https://github.com/vaibhav11123/agentcogs

Python SDK, FastAPI, Postgres, Redis, React. [MIT](https://github.com/vaibhav11123/agentcogs/blob/main/LICENSE). [Contributing](https://github.com/vaibhav11123/agentcogs/blob/main/CONTRIBUTING.md). [Security](https://github.com/vaibhav11123/agentcogs/blob/main/SECURITY.md).
