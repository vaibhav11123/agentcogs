# Post 6 — LangChain Discord (#showcase)

🟢 Just shipped AgentCOGS — per-customer LLM cost attribution for LangGraph

The problem: when your SaaS hits ~20 customers, "what's my gross margin per customer" becomes unanswerable. OpenAI bills you once, not per customer.

The fix:

    pip install agentcogs

    with agentcogs.run(customer_id="cust_42"):
        # your LangGraph code unchanged

You get a dashboard with cost-per-customer, runtime budget caps, anomaly alerts, and one-click Stripe Meter export.

Built on Shekel for provider patching. Runtime caps raise BEFORE the LLM call (sub-1ms Redis).

Free for up to 5 customers. Would love feedback from anyone running LangGraph in production. https://agentcogs.dev
