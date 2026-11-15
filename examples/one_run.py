#!/usr/bin/env python3
"""Post one recorded cost for Vellum Research.

This is the shape of the event `agentcogs.run()` sends after a block exits.
It does not call a model. USD 0.84 is a number in this file, not a measured bill.
"""
from __future__ import annotations

import os
import sys
import time
import uuid

import agentcogs
from agentcogs.client import emit_event_sync


def main() -> None:
    api_key = os.environ.get("AGENTCOGS_API_KEY")
    workspace_id = os.environ.get("AGENTCOGS_WORKSPACE_ID")
    endpoint = os.environ.get("AGENTCOGS_ENDPOINT", "http://localhost:8000")
    if not api_key or not workspace_id:
        print("Set AGENTCOGS_API_KEY and AGENTCOGS_WORKSPACE_ID", file=sys.stderr)
        sys.exit(1)

    agentcogs.init(api_key=api_key, workspace_id=workspace_id, endpoint=endpoint)
    customer = "vellum_research"
    agentcogs.set_customer(customer)
    event = {
        "run_id": str(uuid.uuid4()),
        "customer_id": customer,
        "workflow_id": "research_agent",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": 0.84,
        "models": {},
        "node_costs": {"search": 0.21, "synthesize": 0.63},
        "metadata": {"source": "examples/one_run.py"},
    }
    accepted, err = emit_event_sync(event)
    print(f"customer_id={customer}")
    print(f"workflow_id={event['workflow_id']}")
    print(f"total_usd={event['total_usd']}")
    print(f"run_id={event['run_id']}")
    print(f"ingest_accepted={accepted}")
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
