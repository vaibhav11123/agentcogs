import pytest
from unittest.mock import patch

import agentcogs
from agentcogs import run
from agentcogs.errors import ConfigurationError


def test_run_uses_set_customer(offline_init):
    agentcogs.set_customer("tenant_ctx")
    with patch("agentcogs.budget.fetch_budget") as fb, patch(
        "agentcogs.budget.emit_event"
    ) as emit:
        fb.return_value = {
            "status": "ok",
            "spent_usd": 0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }
        with run(workflow_id="wf") as ctx:
            assert ctx.customer_id == "tenant_ctx"
        assert emit.call_count == 1
        assert emit.call_args[0][0]["customer_id"] == "tenant_ctx"
    agentcogs.set_customer(None)


def test_kwarg_overrides_context(offline_init):
    agentcogs.set_customer("from_context")
    with patch("agentcogs.budget.fetch_budget") as fb, patch(
        "agentcogs.budget.emit_event"
    ) as emit:
        fb.return_value = {
            "status": "ok",
            "spent_usd": 0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }
        with run(customer_id="from_kwarg"):
            pass
        assert emit.call_args[0][0]["customer_id"] == "from_kwarg"
    agentcogs.set_customer(None)


def test_missing_customer_raises(offline_init):
    agentcogs.set_customer(None)
    with pytest.raises(ConfigurationError, match="customer_id required"):
        with run():
            pass
