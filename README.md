# AgentCOGS

AgentCOGS attributes each LLM call to the customer who caused it, sets that cost against the monthly fee, and shows which account stops making money if the calls keep coming.

```bash
pip install agentcogs
```

You sell an agent to other companies. The model provider sends one invoice. AgentCOGS splits that spend by the tenant who caused it. The package is the SDK. It does not call a model, and it does not invent the fee. You name the customer and post the cost of a call you already made.

The sample company is [Patternstack](https://agentcogs.vercel.app). One click, nothing to type. It is a snapshot of a fictional book of business, as of 14 Nov 2026, shipped in the dashboard, so it opens when no API is running. A hosted AgentCOGS API is not serving. To run your own customers, self-host.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/vaibhav11123/agentcogs/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/vaibhav11123/agentcogs/actions/workflows/ci.yml/badge.svg)](https://github.com/vaibhav11123/agentcogs/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentcogs.svg)](https://pypi.org/project/agentcogs/)

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/patternstack.gif" alt="Opening Patternstack. The book margin is 74.6%. Vellum Research is 29.0% so far and the month ends near −52.2%." width="840">

---

## What does Patternstack show?

Forty customers. The month so far looks healthy. Pace is a straight line from the cost so far. It does not forecast a change in behavior. The fee is the monthly amount on the account.

| | So far | If the calls continue |
| --- | ---: | ---: |
| AI cost | $39,613.25 | $84,885.54 |
| Fees | $155,918.00 | $155,918.00 |
| Margin | 74.6% | 45.6% |

Two accounts are where the month breaks. Vellum Research has spent USD 5,822.84 against a fee of USD 8,200: **29.0%** so far, 2,724 runs, and the largest node is `synthesize`. If that spend continues, the month ends near **−52.2%**. Pinnacle Claims is 35.0% so far and ends near −39.3%. The blended 74.6% does not show either of those.

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/screenshots/patternstack-customers.png" alt="Patternstack customers. Blended margin 74.6%. Vellum Research is 29.0% and the month ends near −52.2%." width="880">

Open the account and the same numbers sit next to the call that posted them.

<img src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/screenshots/vellum-research.png" alt="Vellum Research. Margin 29.0%, AI cost USD 5,822.84, fee USD 8,200, and the set_customer call that posts each run." width="880">

```python
import agentcogs

agentcogs.init()  # AGENTCOGS_API_KEY, AGENTCOGS_WORKSPACE_ID, AGENTCOGS_ENDPOINT
agentcogs.set_customer("vellum_research")  # your tenant id, once per request

with agentcogs.run(workflow_id="research_agent"):
    result = agent.invoke(state)
```

If no customer is set, the run stays unattributed. You type the fee, or you pull the subscription from that customer's Stripe account.

`python examples/one_run.py` posts one recorded cost of USD 0.84 for Vellum Research so you can see a row land. It does not call a model.

---

## How do you run it on your own customers?

**Look.** [agentcogs.vercel.app](https://agentcogs.vercel.app) → **Open Patternstack**.

**Run.** From this repo:

```bash
cp .env.selfhost.example .env
docker compose up -d --build
```

Open http://localhost:3000 and choose **Create my workspace**. No email. The next screen has the install command with your key in it:

```bash
pip install agentcogs
```

Point `AGENTCOGS_ENDPOINT` at `http://localhost:8000`. Send one call, open that customer, and type the monthly fee. Margin is the fee minus the cost.

Full steps: [docs/quickstart.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/quickstart.md). Self-host notes: [docs/DEPLOY.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/DEPLOY.md).

---

## Who is it for?

A founder of a product that sells one agent to many companies, priced as a monthly fee, with the model bill arriving as a single invoice. Support, research, claims, intake, document pipelines.

| You already have | AgentCOGS adds |
| --- | --- |
| Langfuse or LangSmith | Which tenant the trace belonged to, and whether that tenant is still profitable |
| LiteLLM | A callback that posts the tenant and the cost. The proxy stays |
| Stripe | The subscription as the fee, and an optional meter for the usage you already attributed |
| The provider invoice | The join from that one number to the customer list |

---

## What can you connect?

| | |
| --- | --- |
| [FastAPI](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/fastapi.md) | Set the tenant from the request |
| [LangGraph](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/langgraph.md) | Wrap the graph |
| [LiteLLM](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/litellm.md) | Post proxy traffic without wrapping the app |
| [Customer import](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/customer-import.md) | Load names and fees before the first run |
| [Slack](https://github.com/vaibhav11123/agentcogs/blob/main/docs/integrations/slack.md) | A spike opens that customer |
| Stripe | Pull subscription fees. Push a daily usage meter |
| Budget | `monthly_budget_usd` raises `CustomerBudgetExceededError` before the next SDK call. A proxy callback records the cost after the call has already run |

Terminal proof for the SDK, the outbox, and a live call: [docs/demo-paths.md](https://github.com/vaibhav11123/agentcogs/blob/main/docs/demo-paths.md).

---

## Does the SDK call a model?

No. It names the customer and posts the cost of a call the application already made.

## Where does the fee come from?

You type the monthly fee, or you pull that customer's Stripe subscription. The SDK does not invent it. Cost is what the SDK reported for the call. It is not a live price list, and it is not the same number as billable usage.

## Is Patternstack a live bill?

No. It is a snapshot of a fictional book, as of 14 Nov 2026, shipped in the dashboard. It opens when no API is running. A hosted AgentCOGS API is not serving.

## When does the budget stop a call?

`monthly_budget_usd` raises `CustomerBudgetExceededError` before the next SDK call. A proxy callback records the cost after the call has already run. Ingest itself does not block.

---

## Repo

| Path | |
| --- | --- |
| `src/agentcogs/` | The SDK |
| `backend/` | Ingest, margin, pace, budgets |
| `dashboard/` | The book |
| `examples/one_run.py` | One recorded cost, no model call |
| `docs/` | [Index](https://github.com/vaibhav11123/agentcogs/blob/main/docs/README.md) |

- Sample: https://agentcogs.vercel.app
- Package: https://pypi.org/project/agentcogs/
- Source: https://github.com/vaibhav11123/agentcogs

Python SDK, FastAPI, Postgres, Redis, React. [MIT](https://github.com/vaibhav11123/agentcogs/blob/main/LICENSE). [Contributing](https://github.com/vaibhav11123/agentcogs/blob/main/CONTRIBUTING.md). [Security](https://github.com/vaibhav11123/agentcogs/blob/main/SECURITY.md).
