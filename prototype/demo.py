"""Week 0 demo prototype — no backend, no DB.

Run on validation calls:  python prototype/demo.py
"""
import json
import time
import uuid
from contextlib import contextmanager


@contextmanager
def run(customer_id: str, workflow_id: str = "default"):
    """Mock run() that prints a realistic event instead of POSTing."""
    run_id = str(uuid.uuid4())
    start = time.time()

    print(f"\n→ agentcogs.run(customer_id={customer_id!r}, workflow_id={workflow_id!r}) entered")
    print("  remaining_budget_usd=$1,247.32  (mock — would come from Redis)")

    try:
        yield
    finally:
        elapsed = time.time() - start
        event = {
            "run_id": run_id,
            "customer_id": customer_id,
            "workflow_id": workflow_id,
            "ts": int(time.time()),
            "status": "completed",
            "total_usd": 0.4231,
            "models": {
                "claude-3-5-sonnet": {
                    "input_tokens": 1200,
                    "cache_read_input_tokens": 3800,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 612,
                    "usd": 0.4231,
                }
            },
            "node_costs": {
                "plan": 0.0421,
                "search": 0.1822,
                "synthesize": 0.1531,
                "critique": 0.0457,
            },
            "duration_ms": int(elapsed * 1000),
        }
        print("\n📊 COST EVENT (would POST to https://api.agentcogs.dev):")
        print(json.dumps(event, indent=2))
        print(f"\n→ Would update margin for {customer_id}:")
        # Aligned with tools/personas.py + MTD calibration (seed=42)
        cost_mtd = 5822.00
        revenue_mtd = 8200.00
        margin = (revenue_mtd - cost_mtd) / revenue_mtd * 100
        new_cost = cost_mtd + event["total_usd"]
        new_margin = (revenue_mtd - new_cost) / revenue_mtd * 100
        print(f"  AI cost MTD:  ${cost_mtd:,.2f} (+${event['total_usd']:.4f})")
        print(f"  Revenue MTD:  ${revenue_mtd:,.2f}")
        print(f"  Margin:       {margin:.1f}% → {new_margin:.1f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("  AgentCOGS — 30-second demo")
    print("=" * 60)
    print()
    print("Your existing code:")
    print()
    print("    from my_agent import research_graph")
    print("    result = research_graph.invoke({'query': 'analyze Q4 contracts'})")
    print()
    input("→ Press Enter to add AgentCOGS (2 lines)...")
    print()
    print("After:")
    print()
    print("    import agentcogs                                          # line 1")
    print("    with agentcogs.run(customer_id='techflow_inc'):           # line 2")
    print("        result = research_graph.invoke({'query': '...'})")
    print()
    input("→ Press Enter to run it...")

    with run(customer_id="techflow_inc", workflow_id="research_agent"):
        print("  ... [research_graph.invoke() executing] ...")
        time.sleep(1.5)
        print("  ... agent completed in 1.5s, 4 nodes, 5612 tokens ...")

    print()
    print("=" * 60)
    print("  That's it. Same code. One extra line. Per-customer attribution.")
    print("=" * 60)
