# LiteLLM integration

Use AgentCOGS with a [LiteLLM](https://github.com/BerriAI/litellm) proxy for per-customer LLM cost and margin.

**Requires:** AgentCOGS workspace API key, `workspace_id`, and ingest endpoint ([quickstart.md](../quickstart.md)).

**Attribution:** Set LiteLLM `user` to your B2B `customer_id`, or pass `metadata.agentcogs_customer_id`. See [customer-id.md](../concepts/customer-id.md).

---

## Official callback (upstream PR pending)

Once [BerriAI/litellm#28255](https://github.com/BerriAI/litellm/pull/28255) merges, enable with one line:

```python
import litellm

litellm.success_callback = ["agentcogs"]
```

```yaml
litellm_settings:
  callbacks: ["agentcogs"]
```

Set `AGENTCOGS_API_KEY`, `AGENTCOGS_WORKSPACE_ID`, and optional `AGENTCOGS_ENDPOINT` in the environment.

**Proxy attribution:** `AGENTCOGS_CHARGE_BY` — `end_user_id` (default), `user_id`, or `team_id` (same pattern as Lago). Client `metadata.agentcogs_customer_id` is not used on proxy traffic.

Docs page: submit to [BerriAI/litellm-docs](https://github.com/BerriAI/litellm-docs) — draft in [internal/litellm-docs-agentcogs.md](../internal/litellm-docs-agentcogs.md). User guide: [integrations/litellm.md](litellm.md).

**Local smoke:** from repo root, with demo stack running (`./tools/start_demo.sh`):

```bash
pip install -e /path/to/litellm-fork   # branch feat/agentcogs-integration until merge
python scripts/verify_litellm_callback.py   # needs OPENAI_API_KEY
```

---

## User-landed callback (works today)

Copy the module below into your project if you cannot wait on upstream merge.

---

## Environment

```bash
export AGENTCOGS_API_KEY="acg_live_..."
export AGENTCOGS_WORKSPACE_ID="your-uuid"
export AGENTCOGS_ENDPOINT="https://api.agentcogs.dev"   # or http://localhost:8000
```

---

## Callback module

Save as `agentcogs_litellm.py` (or add to your package) and register it in LiteLLM config.

```python
"""LiteLLM CustomLogger → AgentCOGS POST /v1/ingest."""
import os
import time
import uuid

import httpx
from litellm.integrations.custom_logger import CustomLogger


def _usage_int(usage, key: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(key, 0) or 0)
    return int(getattr(usage, key, 0) or 0)


def _build_event(kwargs, *, status: str, error: str | None = None) -> dict | None:
    meta = kwargs.get("metadata") or {}
    customer_id = kwargs.get("user") or meta.get("agentcogs_customer_id")
    if not customer_id:
        return None

    model = kwargs.get("model") or "unknown"
    cost = float(kwargs.get("response_cost") or 0)
    usage = kwargs.get("usage")
    start = kwargs.get("start_time")
    ts = int(start.timestamp()) if start is not None and hasattr(start, "timestamp") else int(time.time())

    return {
        "run_id": str(uuid.uuid4()),
        "workspace_id": os.environ["AGENTCOGS_WORKSPACE_ID"],
        "customer_id": str(customer_id),
        "workflow_id": meta.get("agentcogs_workflow_id", "default"),
        "ts": ts,
        "status": status,
        "total_usd": cost,
        "models": {
            model: {
                "input_tokens": _usage_int(usage, "prompt_tokens"),
                "output_tokens": _usage_int(usage, "completion_tokens"),
                "usd": cost,
            }
        },
        "node_costs": {},
        "metadata": {"source": "litellm"},
        "error": error,
    }


async def _post(event: dict) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            f"{os.environ['AGENTCOGS_ENDPOINT'].rstrip('/')}/v1/ingest",
            json=event,
            headers={
                "Authorization": f"Bearer {os.environ['AGENTCOGS_API_KEY']}",
                "X-AgentCOGS-SDK-Version": "litellm-callback/0.1.0",
            },
        )
        resp.raise_for_status()


class AgentCOGSLogger(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        event = _build_event(kwargs, status="completed")
        if event:
            await _post(event)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        err = str(kwargs.get("exception", "error"))[:500]
        event = _build_event(kwargs, status="error", error=err)
        if event:
            await _post(event)
```

---

## LiteLLM config

Register the logger class in your LiteLLM deployment (exact registration depends on your LiteLLM version — see LiteLLM [custom callbacks](https://docs.litellm.ai/docs/observability/custom_callback) docs).

Example pattern:

```yaml
litellm_settings:
  callbacks: ["agentcogs_litellm.AgentCOGSLogger"]
```

Ensure each completion sets tenant context:

```python
import litellm

litellm.completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hi"}],
    user="acme_corp",  # → AgentCOGS customer_id
    metadata={"agentcogs_workflow_id": "support_bot"},
)
```

---

## Verify

1. `agentcogs.ping()` from a machine that can reach your API (or use [quickstart](../quickstart.md) from the SDK).
2. Run one LiteLLM completion with `user="test_tenant"`.
3. Open dashboard **Customers** — row should appear within ~60s.

---

## Native SDK alternative

If you control application code directly, prefer the Python SDK (`agentcogs.run()`) over a proxy callback — fewer moving parts. See [quickstart.md](../quickstart.md) and [fastapi.md](fastapi.md).

---

## Upstream status

| Item | Link |
|------|------|
| Issue | [BerriAI/litellm#28254](https://github.com/BerriAI/litellm/issues/28254) |
| PR | [BerriAI/litellm#28255](https://github.com/BerriAI/litellm/pull/28255) |

An official `docs.litellm.ai` page is for discoverability (SEO), not required for the integration to work. See [DISTRIBUTION_PLAYBOOK.md](../DISTRIBUTION_PLAYBOOK.md).
