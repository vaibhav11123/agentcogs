"""Test 8 — SDK talking to local backend (backend must be on :8000)."""
import os
import time

import agentcogs

agentcogs.init(
    api_key=os.environ.get("API_KEY", "acg_live_TESTKEY"),
    workspace_id="ws_local",
    endpoint=os.environ.get("API_URL", "http://localhost:8000"),
)

use_openai = os.environ.get("SKIP_OPENAI") != "1" and bool(os.environ.get("OPENAI_API_KEY"))

if use_openai:
    from openai import OpenAI

    client = OpenAI()
    with agentcogs.run(customer_id="cust_integration", workflow_id="test"):
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hi"}],
        )
else:
    with agentcogs.run(customer_id="cust_integration", workflow_id="test"):
        pass  # zero-cost run; still tests ingest path

time.sleep(2)
print("✅ SDK run completed — check Postgres:")
print(
    '   docker compose -f backend/docker-compose.yml exec postgres '
    'psql -U postgres -d agentcogs -c '
    '"SELECT id, customer_id, total_usd FROM cost_events ORDER BY created_at DESC LIMIT 3;"'
)
