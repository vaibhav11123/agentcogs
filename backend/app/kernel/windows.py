"""Pane deltas for a cache write whose readers change. Pure. No database."""

from __future__ import annotations

from datetime import datetime, timedelta

from agentcogs.kernel import split_equal


def close_or_refine(users_before: list[str], users_after: list[str], write_micro: int) -> list[dict]:
    before = split_equal(write_micro, users_before)
    after = split_equal(write_micro, users_after)
    lines = []
    for call_id in sorted(set(before) | set(after)):
        lines.append({"call_id": call_id, "micro": after.get(call_id, 0) - before.get(call_id, 0)})
    return lines


def may_close(recorded_at: datetime | None, now: datetime) -> bool:
    if recorded_at is None:
        return False
    return now - recorded_at < timedelta(minutes=15)


def remember_pane(store: dict, pane_id: str, lines: list) -> None:
    if pane_id not in store:
        store[pane_id] = lines
