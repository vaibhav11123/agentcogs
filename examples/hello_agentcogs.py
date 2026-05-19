#!/usr/bin/env python3
"""Canonical quickstart — verify SDK → ingest → dashboard.

Documented in docs/quickstart.md and examples/README.md.

Requires:
  export AGENTCOGS_API_KEY='acg_live_...'
  export AGENTCOGS_WORKSPACE_ID='...'
  export AGENTCOGS_ENDPOINT='http://localhost:8000'  # optional (production default)

Optional:
  export AGENTCOGS_TEST_TENANT='hello_tenant'
  export OPENAI_API_KEY='...'      # or ANTHROPIC_API_KEY — omit for zero-cost ingest test
  export ANTHROPIC_API_KEY='...'
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    import agentcogs

    api_key = os.environ.get("AGENTCOGS_API_KEY")
    workspace_id = os.environ.get("AGENTCOGS_WORKSPACE_ID")
    endpoint = os.environ.get("AGENTCOGS_ENDPOINT", "http://localhost:8000")

    if not api_key or not workspace_id:
        print(
            "Set AGENTCOGS_API_KEY and AGENTCOGS_WORKSPACE_ID "
            "(from dashboard Settings).",
            file=sys.stderr,
        )
        sys.exit(1)

    agentcogs.init(api_key=api_key, workspace_id=workspace_id, endpoint=endpoint)

    print("Ping:", agentcogs.ping())

    tenant = os.environ.get("AGENTCOGS_TEST_TENANT", "hello_tenant")
    agentcogs.set_customer(tenant)

    with agentcogs.run(workflow_id="hello_agentcogs") as ctx:
        if os.environ.get("OPENAI_API_KEY"):
            from openai import OpenAI

            OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hi in one word."}],
                max_tokens=5,
            )
        elif os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic

            anthropic.Anthropic().messages.create(
                model="claude-haiku-4-5",
                max_tokens=5,
                messages=[{"role": "user", "content": "Say hi in one word."}],
            )
        else:
            print("(no LLM key — sending zero-cost run for ingest test)")

    status = ctx.wait_for_ingest(timeout=10)
    print(f"run_id={ctx.run_id} ingest_accepted={status.accepted}")
    if status.error:
        print(f"ingest note: {status.error}", file=sys.stderr)
    print(f"Open dashboard → Customers → look for tenant {tenant!r}")


if __name__ == "__main__":
    main()
