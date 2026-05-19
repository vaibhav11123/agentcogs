# Post 4 — DEV reply (Gregory Zem agentic billing)

This resonates. The "agent runs at 3am, retry loop fires 400 times, $72 bill" pattern is exactly what made us build runtime budget caps at the SDK layer.

The trick: budget check at context entry (sub-1ms Redis HGET) lets you raise an exception BEFORE the OpenAI client is touched. Exceeded cap → $0 in provider fees.

    with agentcogs.run(customer_id="cust_42"):
        # raises CustomerBudgetExceededError if over $5/mo cap

Open: pip install agentcogs. Hosted dashboard + Stripe Meter sync if useful — https://agentcogs.dev
