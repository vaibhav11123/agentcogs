"""Lane mapping and the budget flag the SDK is allowed to raise on."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentcogs import CustomerBudgetExceededError, run
from agentcogs._shekel_compat import lanes_from_usage, normalize_summary
from agentcogs.kernel import price_call

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "kernel" / "price_book_fixture_v1.json"


def test_openai_docs_usage_prices_to_15150():
    lanes = lanes_from_usage(
        "openai",
        {
            "input_tokens": 12000,
            "input_tokens_details": {"cached_tokens": 4000},
            "cache_write_tokens_details": {"ttl_30m_tokens": 3000, "ttl_12h_tokens": 4000},
            "output_tokens": 0,
            "output_tokens_details": {"reasoning_tokens": 50},
        },
    )
    book = json.loads(FIXTURE.read_text())
    book["usd_per_million"] = {"input": 1, "output": 15}
    _priced, total = price_call(lanes, book)
    assert total == 15150
    assert lanes["reasoning"] == 50


def test_normalize_summary_shape_is_unchanged():
    out = normalize_summary(
        {
            "claude-3-5-sonnet": {
                "input_tokens": 500,
                "cache_read_input_tokens": 8000,
                "cache_creation_input_tokens": 200,
                "output_tokens": 100,
                "cost": 0.025,
            }
        }
    )
    assert out["claude-3-5-sonnet"]["input_tokens"] == 8700


def test_enforce_false_does_not_raise_and_a_missing_flag_still_does(offline_init):
    class FakeCtx:
        def summary_data(self):
            return {"total_spent": 0, "by_model": {}}

    class FakeBudget:
        def __enter__(self):
            return FakeCtx()

        def __exit__(self, *args):
            return False

    with patch("agentcogs.budget.fetch_budget") as fetch, patch("agentcogs.budget.emit_event"), patch(
        "agentcogs.budget.shekel_budget", return_value=FakeBudget()
    ):
        fetch.return_value = {
            "status": "exceeded",
            "enforce": False,
            "decision": "exceeded",
            "spent_usd": 5,
            "budget_usd": 5,
            "remaining_usd": 0,
        }
        with run(customer_id="cust_ok"):
            pass
        fetch.return_value = {
            "status": "busy",
            "enforce": True,
            "spent_usd": 1,
            "budget_usd": 1,
            "remaining_usd": 0,
        }
        with run(customer_id="cust_busy"):
            pass
        fetch.return_value = {
            "status": "exceeded",
            "spent_usd": 5,
            "budget_usd": 5,
            "remaining_usd": 0,
        }
        with pytest.raises(CustomerBudgetExceededError):
            with run(customer_id="cust_block"):
                pass
