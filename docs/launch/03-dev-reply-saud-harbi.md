# Post 3 — DEV reply (@saud_harbi per-customer attribution)

This was exactly the problem we hit at ~40 customers — your post nailed why it's nearly impossible to solve with just LangSmith traces.

We ended up building the attribution layer as a 2-line wrapper:

    pip install agentcogs

    with agentcogs.run(customer_id="cust_42"):
        # your existing LangGraph code unchanged

It uses Shekel underneath for provider patching, but adds per-customer aggregation, idempotent Postgres ingest, and runtime budget caps (sub-1ms Redis check before the LLM call fires).

The one detail I wish we'd known earlier: Anthropic prompt caching splits input tokens across three fields. If your attribution code only reads `input_tokens`, you're undercounting cached Claude calls by ~10–17×.

Wrapped it into AgentCOGS — happy to send early access if useful, free for up to 5 customers. https://agentcogs.dev
