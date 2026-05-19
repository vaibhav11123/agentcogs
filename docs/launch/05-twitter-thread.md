# Post 5 — Twitter/X thread (Tuesday 11am EST)

## Tweet 1

We spent 3 Sundays trying to figure out which of our LangGraph customers were profitable.

OpenAI sends one bill. Anthropic sends another. Neither has a customer_id column.

So we built AgentCOGS. 2 lines of Python, per-customer gross margin. Thread 👇

## Tweet 2

The SDK:

    pip install agentcogs

    with agentcogs.run(customer_id="cust_42"):
        # any LLM call here, unchanged

Every openai / anthropic / langgraph call inside the block gets attributed to cust_42. Background thread posts the cost event — never blocks your code.

## Tweet 3

The dashboard answers the question we couldn't answer in spreadsheets:

TechFlow Inc: $5,800 cost / $8,200 rev = 29% margin
Acme Corp:    $3,100 cost / $12,400 rev = 75% margin

Two of our "best" customers were burning more than they paid us.

## Tweet 4

Runtime budget caps that actually work:

Most tools pause telemetry when the cap hits — but the provider still bills you.

We do a sub-1ms Redis check at context entry. Exceeded cap → exception BEFORE any LLM call fires.

## Tweet 5

Bug that bit us: Anthropic prompt caching splits input tokens across THREE fields. Reading only `input_tokens` undercounts cached Claude by ~17×.

## Tweet 6

Free for up to 5 customers. Stripe Meter sync, anomaly alerts, monthly CSV close report.

https://agentcogs.dev
