"""Shekel + LLM smoke test — no AgentCOGS ingest.

For real SDK → dashboard:  python3 examples/hello_agentcogs.py
For sales mock (no keys):   python3 prototype/demo.py

Uses Claude (Anthropic) by default. Set ANTHROPIC_API_KEY.

Optional: LLM_PROVIDER=openai|groq with OPENAI_API_KEY or GROQ_API_KEY.
"""
import json
import os
import time
import uuid
from contextlib import contextmanager

from shekel import budget

# Dated 3.5 IDs return 404 on newer accounts; use Haiku 4.5 alias (override via CLAUDE_MODEL).
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"
MAX_OUTPUT_TOKENS = 64
# Anthropic list price for Haiku 4.5: $1/M input, $5/M output → per 1k tokens for Shekel.
CLAUDE_HAIKU_45_PER_1K = {"input": 0.001, "output": 0.005}


@contextmanager
def run(
    customer_id: str,
    workflow_id: str = "default",
    *,
    price_per_1k_tokens: dict[str, float] | None = None,
):
    run_id = str(uuid.uuid4())
    with budget(
        name=customer_id,
        max_usd=5.00,
        price_per_1k_tokens=price_per_1k_tokens,
    ) as b:
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


def _call_claude() -> str:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "Set ANTHROPIC_API_KEY to run the Claude prototype.\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'"
        )
    from anthropic import Anthropic

    model = os.environ.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    client = Anthropic()
    client.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    )
    return f"claude ({model})"


def _call_groq() -> str:
    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit("Set GROQ_API_KEY to run the Groq prototype.")
    from openai import OpenAI

    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    client.chat.completions.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    )
    return f"groq ({model})"


def _call_openai() -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY to run the OpenAI prototype.")
    from openai import OpenAI

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI()
    client.chat.completions.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    )
    return f"openai ({model})"


def call_llm() -> str:
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider in ("anthropic", "claude"):
        return _call_claude()
    if provider == "groq":
        return _call_groq()
    if provider == "openai":
        return _call_openai()
    raise SystemExit(f"Unknown LLM_PROVIDER={provider!r} (use anthropic, groq, or openai)")


def _shekel_pricing() -> dict[str, float] | None:
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider in ("anthropic", "claude"):
        return CLAUDE_HAIKU_45_PER_1K
    return None


if __name__ == "__main__":
    print(f"→ Provider: {os.environ.get('LLM_PROVIDER', 'anthropic')}")
    with run(
        customer_id="cust_42",
        workflow_id="prototype",
        price_per_1k_tokens=_shekel_pricing(),
    ):
        label = call_llm()
    print(f"✓ Completed live call via {label}")
