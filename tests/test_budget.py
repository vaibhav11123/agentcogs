import pytest
from unittest.mock import patch
from agentcogs import run, CustomerBudgetExceededError


def test_budget_exceeded_raises_before_yield(offline_init):
    with patch("agentcogs.budget.fetch_budget") as fb:
        fb.return_value = {
            "status": "exceeded",
            "spent_usd": 5.0,
            "budget_usd": 5.0,
            "remaining_usd": 0,
        }
        with pytest.raises(CustomerBudgetExceededError) as exc:
            with run(customer_id="cust_x"):
                pytest.fail("body should not execute")
        assert exc.value.customer_id == "cust_x"


def test_normal_run_emits_event(offline_init):
    class FakeCtx:
        def summary_data(self):
            return {"total_spent": 0, "by_model": {}}

    class FakeBudget:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return FakeCtx()

        def __exit__(self, *a):
            return False

    with patch("agentcogs.budget.fetch_budget") as fb, \
         patch("agentcogs.budget.emit_event") as emit, \
         patch("agentcogs.budget.shekel_budget", FakeBudget):
        fb.return_value = {"status": "ok", "spent_usd": 0, "budget_usd": None,
                           "remaining_usd": float("inf")}
        with run(customer_id="cust_y", workflow_id="test"):
            pass
        # threading delay — give it a tick
        import time

        time.sleep(0.15)
        assert emit.call_count == 1
        event = emit.call_args[0][0]
        assert event["customer_id"] == "cust_y"
        assert event["workflow_id"] == "test"
        assert len(event["run_id"]) >= 8
        assert "workspace_id" not in event
