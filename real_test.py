"""real_test.py — actually hits OpenAI, tracks real cost."""
import os

import agentcogs

if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit("Set OPENAI_API_KEY to run this test")

agentcogs.init(offline=True, workspace_id="ws_local")

from openai import OpenAI

client = OpenAI()

with agentcogs.run(customer_id="cust_real", workflow_id="greeting") as ctx:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hi in 5 words"}],
    )
    print("LLM response:", resp.choices[0].message.content)

summary = ctx.summary_data()
total = summary.get("total_cost") or summary.get("total_spent") or 0
print("\n📊 Cost summary:")
print(f"   Total: ${float(total):.6f}")
print(f"   Models: {summary.get('by_model')}")
