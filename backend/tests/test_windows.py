"""Pane deltas match the late-reader vector and a pane is remembered once."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.kernel.windows import close_or_refine, may_close, remember_pane

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "kernel"


def test_late_reader_deltas_sum_to_zero():
    case = next(item for item in json.loads((FIXTURES / "panes_v1.json").read_text())["cases"] if item["id"] == "late-reader-deltas")
    lines = close_or_refine(case["pane_before_users"], case["pane_after_users"], case["write_micro"])
    got = {line["call_id"]: line["micro"] for line in lines}
    assert got == case["expected_deltas"]
    assert sum(got.values()) == 0


def test_remember_pane_once_and_missing_heartbeat_does_not_close():
    store: dict = {}
    remember_pane(store, "seg:k:1", [{"call_id": "a", "micro": 1}])
    remember_pane(store, "seg:k:1", [{"call_id": "a", "micro": 9}])
    assert store["seg:k:1"] == [{"call_id": "a", "micro": 1}]
    now = datetime.now(timezone.utc)
    assert may_close(None, now) is False
    assert may_close(now - timedelta(minutes=14), now) is True
    assert may_close(now - timedelta(minutes=15), now) is False
