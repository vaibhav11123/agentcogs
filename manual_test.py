"""Manual smoke test — offline mode, no backend needed."""
import pathlib
import sqlite3

import agentcogs

# 1. Init in offline mode (no API key needed)
agentcogs.init(offline=True, workspace_id="ws_local_test")

# 2. Mock an LLM call by directly invoking Shekel
with agentcogs.run(customer_id="cust_demo", workflow_id="test_workflow") as ctx:
    print(f"✅ Inside run() context: ctx={ctx}")

print("✅ Exited run() context — event should have been queued")

# 3. Check the outbox
db = pathlib.Path.home() / ".agentcogs" / "outbox.db"
if db.exists():
    conn = sqlite3.connect(str(db))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='outbox'"
    ).fetchone()
    if not tables:
        print("📦 Outbox DB exists but is empty (offline mode — no events queued)")
    else:
        rows = conn.execute("SELECT run_id, attempts FROM outbox").fetchall()
        print(f"📦 Outbox contains {len(rows)} pending event(s)")
        for run_id, attempts in rows:
            print(f"   - {run_id} (attempts={attempts})")
    conn.close()
else:
    print("📦 Outbox DB does not exist (expected in offline mode)")
