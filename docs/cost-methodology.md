# How the number is calculated

AI margin is the monthly fee minus the attributed AI cost, divided by the fee.

```text
AI margin = (monthly fee − attributed AI cost) / monthly fee
```

It is the contribution of that fee after the AI cost attributed to the customer. It is not total customer profitability, and it is not accounting gross margin.

## What goes into the cost

On a workspace you run yourself, the month-to-date cost is the sum of `total_usd` on that customer's cost events since the first instant of the current month, in UTC.

`total_usd` is the cost posted for one `run()`. The SDK does not call a model. When the block contains an OpenAI or Anthropic call, the SDK reads the usage object on the response. A chat completion reports `prompt_tokens`. Cached tokens and cache writes on that object are included. The SDK prices those lanes with the book shipped in the package. It does not look up a live provider price list. The server prices the same lanes with the workspace book and rejects the event if the totals disagree by more than one micro-USD. Read a stream inside the block. If the block makes no instrumented call, the posted cost is zero.

`examples/one_run.py` posts a recorded `total_usd` of 0.84. That number is not a model call. It only shows that ingest stored the event you sent.

A duplicate `run_id` is accepted as a duplicate and is not stored twice.

## What goes into the fee

The fee is `monthly_revenue_usd` on the customer.

You type it, or you pull it from Stripe. The Stripe pull lists that customer's active subscriptions and sums the monthly value of active, non-metered prices. A day, week, or year price is normalized to a month. Metered prices are skipped. A percent or amount coupon is applied when Stripe expanded it on the subscription. The SDK does not invent the fee.

The whole monthly fee is set against cost so far. The fee is not divided by the day of the month.

## Pace

Pace is a straight line. Projected cost is month-to-date cost times the number of days in the month, divided by the day of the month. The projected margin uses that cost against the full monthly fee.

The live API does not draw a pace before the third day of the month, so one early spike is not multiplied across the month. Pace does not forecast a change in behavior, a new model, or a refund.

The public Patternstack sample is a frozen fictional book. Its pace is calculated from 14 Nov 2026, not from today's date.

## What the number leaves out

People, infrastructure, support, and payment processing. Tax. Refunds, credits, and proration as their own ledger. Currency conversion. A match against the provider's invoice. Costs from calls that were never attributed to a customer.

The CSV download uses the column `ai_margin_pct` for the same ratio. When the fee is zero, that cell is blank. The dashboard also leaves the margin blank when the fee is zero.

## Where this is enforced

The customer list and the customer page read the formula above. The budget check is a separate control. It does not change the margin. See [budget-semantics.md](budget-semantics.md).
