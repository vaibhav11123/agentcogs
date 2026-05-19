# Post 2 — Show HN (Tuesday 8am EST)

## Title

Show HN: AgentCOGS – per-customer LLM cost attribution for agent SaaS (2-line SDK)

## URL

https://agentcogs.dev

## First comment (post immediately after submitting)

Author here. Built this after our LangGraph SaaS hit ~40 customers and we realized we had no idea which were profitable.

The setup is:

    pip install agentcogs

    with agentcogs.run(customer_id="cust_42"):
        # any openai / anthropic / langgraph code

You get a dashboard showing AI cost per customer, joined against revenue, with gross margin. Plus runtime budget caps that raise an exception BEFORE the LLM call fires.

Technical bits:

- Fire-and-forget SDK with SQLite outbox for offline retry
- Sub-1ms Redis budget check before context entry
- run_id as Postgres PK + Stripe Meter identifier (no double-billing)
- Anthropic cache token normalization (3 fields, not 1)

Free for up to 5 customers. Happy to answer questions.
