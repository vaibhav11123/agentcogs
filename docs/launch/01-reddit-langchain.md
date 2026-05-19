# Post 1 — r/LangChain (Monday 9am EST)

## Title

How we handle per-customer LLM cost attribution for LangGraph agents (full Postgres schema + Shekel integration, 2-line SDK)

## Body

Built this after spending three Sundays trying to figure out which of our customers were actually profitable. OpenAI gives you a single monthly bill. Anthropic gives you another. Neither tells you "customer X cost $487 this month and generated $200 of revenue."

Sharing the architecture because every LangGraph team I've talked to is solving this with spreadsheets.

## The 2-line SDK side

    pip install agentcogs

    import agentcogs
    agentcogs.init(api_key="acg_live_...")

    with agentcogs.run(customer_id="cust_42", workflow_id="summarize"):
        result = my_langgraph_agent.invoke({"input": "..."})

Every OpenAI/Anthropic/Bedrock call inside the `with` block is attributed to `cust_42`. Built on top of Shekel (which does the actual provider patching) — we add the per-customer aggregation, budget caps, and dashboard.

## The Postgres schema (the part that matters)

    CREATE TABLE cost_events (
        id              UUID PRIMARY KEY,    -- = run_id from SDK (idempotency)
        workspace_id    UUID NOT NULL,
        customer_id     UUID NOT NULL,
        workflow_id     TEXT NOT NULL,
        ts              TIMESTAMPTZ NOT NULL,
        total_usd       NUMERIC(12,6),
        model_breakdown JSONB,
        node_breakdown  JSONB,
        stripe_synced_at TIMESTAMPTZ
    );
    CREATE INDEX idx_events_ws_cust_ts
        ON cost_events(workspace_id, customer_id, ts DESC);
    CREATE INDEX idx_events_sync_pending
        ON cost_events(ts) WHERE stripe_synced_at IS NULL;

The `run_id` UUID is the primary key. SDK retries from the outbox queue are silently deduplicated via `ON CONFLICT DO NOTHING`. Partial index on the unsynced events makes the nightly Stripe sync query instant regardless of table size.

## Three things that bit us

**1. Anthropic prompt caching splits input tokens across 3 fields.**

**2. Supabase pooler in transaction mode breaks prepared statements.** asyncpg needs `statement_cache_size=0` on port 6543.

**3. Real-time budget caps need to fail BEFORE the LLM call fires.** We do a Redis HGET on context entry and raise `CustomerBudgetExceededError` before any provider client is touched.

## The thing nobody talks about: gross margin per customer

Once you have per-customer cost, you can join it against per-customer revenue and finally see the leaderboard.

## Wrapped it into a product

We turned this into AgentCOGS — same SDK, hosted dashboard, free for up to 5 customers. Comment or DM if you want early access.

Repo / docs: https://agentcogs.dev
