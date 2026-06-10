from unittest.mock import patch

from agentcogs.budget import _cap_metadata


def test_oversized_metadata_truncated(offline_init):
    big = {f"k{i}": "v" * 200 for i in range(150)}
    capped = _cap_metadata(big)
    assert len(capped) <= 100

    with patch("agentcogs.budget.fetch_budget") as fb, patch(
        "agentcogs.budget.emit_event"
    ) as emit:
        fb.return_value = {
            "status": "ok",
            "spent_usd": 0,
            "budget_usd": None,
            "remaining_usd": float("inf"),
        }

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

        with patch("agentcogs.budget.shekel_budget", FakeBudget):
            from agentcogs import run

            with run(customer_id="c", metadata=big):
                pass

        event = emit.call_args[0][0]
        assert "workspace_id" not in event
        assert len(event["metadata"]) <= 100
