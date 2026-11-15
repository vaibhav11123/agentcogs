<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/brand/10-agentcogs-lockup-white.png">
    <img alt="AgentCOGS" src="https://raw.githubusercontent.com/vaibhav11123/agentcogs/main/docs/assets/brand/1-agentcogs-lockup-primary.png" width="420">
  </picture>
</p>


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
