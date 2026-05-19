"""Week 0 demo — run on validation calls: python prototype.py"""
import json
import time
import uuid
from contextlib import contextmanager

from shekel import budget


@contextmanager
def run(customer_id: str, workflow_id: str = "default"):
    run_id = str(uuid.uuid4())
    with budget(name=customer_id, max_usd=5.00) as b:
        yield b
    summary = b.summary_data()
    total = summary.get("total_spent", summary.get("total_cost", 0))
    event = {
        "run_id": run_id,
        "customer_id": customer_id,
        "workflow_id": workflow_id,
        "ts": int(time.time()),
        "total_usd": float(total),
        "models": summary.get("by_model", {}),
    }
    print("📊 COST EVENT:", json.dumps(event, indent=2))


if __name__ == "__main__":
    from openai import OpenAI

    client = OpenAI()
    with run(customer_id="cust_42"):
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
        )
