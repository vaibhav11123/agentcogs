"""Public kernel tests. Expected numbers come from tests/fixtures/kernel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentcogs.kernel import (
    allocate_case,
    book_for,
    lane_micro,
    mul_div_round_half_up,
    price_call,
    split_equal,
)

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "kernel"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_half_up_and_overflow():
    assert mul_div_round_half_up(5, 2) == 3
    assert mul_div_round_half_up(1, 3) == 0
    with pytest.raises(ValueError, match="^AMOUNT_OVERFLOW$"):
        lane_micro(2**62, 4, 2, 1)


def test_allocate_vectors_match_oracle():
    fixture = _load("price_book_fixture_v1.json")
    for case in _load("allocate_v1.json")["cases"]:
        if case.get("mode") == "error":
            with pytest.raises(ValueError) as exc:
                allocate_case(case, fixture)
            assert str(exc.value) == case["error"]
            continue
        got = allocate_case(case, fixture)
        expected = case["expected"]
        assert got["incurred_micro"] == expected["incurred_micro"], case["id"]
        assert got["allocated_micro"] == expected["allocated_micro"], case["id"]
        assert sum(got["incurred_micro"].values()) == sum(got["allocated_micro"].values())
        if "share_micro" in expected:
            assert got["share_micro"] == expected["share_micro"], case["id"]
        if "lane_micro" in expected:
            priced, _ = price_call(case["calls"][0]["lanes"], book_for(case, fixture))
            for lane, micro in expected["lane_micro"].items():
                assert priced[lane] == micro
        if case["id"] == "airport-two-calls":
            assert sum(got["allocated_micro"].values()) == 6150


def test_pane_deltas_sum_to_zero():
    for case in _load("panes_v1.json")["cases"]:
        before = split_equal(case["write_micro"], case["pane_before_users"])
        after = split_equal(case["write_micro"], case["pane_after_users"])
        assert before == case["expected_share_before"]
        assert after == case["expected_share_after"]
        deltas = {user: after.get(user, 0) - before.get(user, 0) for user in set(before) | set(after)}
        assert deltas == case["expected_deltas"]
        assert sum(deltas.values()) == 0
