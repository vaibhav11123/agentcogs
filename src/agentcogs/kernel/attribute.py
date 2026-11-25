"""Closed-form split of a nested cache write. Incurred is the provider charge."""

from __future__ import annotations

import json

from .money import lane_micro

ROLE_TO_LANE = {
    "write_5m": "cache_write_5m",
    "write_1h": "cache_write_1h",
    "write_30m": "cache_write_30m",
    "write_12h": "cache_write_12h",
}


def price_call(lanes: dict, book: dict) -> tuple[dict, int]:
    priced: dict[str, int] = {}
    total = 0
    reasoning = book.get("reasoning_lane", "reasoning")
    for lane, tokens in lanes.items():
        if lane == reasoning:
            priced[lane] = 0
            continue
        spec = book["lanes"][lane]
        micro = lane_micro(int(tokens), int(book["usd_per_million"][spec["base"]]), int(spec["num"]), int(spec["den"]))
        priced[lane] = micro
        total += micro
    return priced, total


def segments_nest(segments: list[dict]) -> bool:
    by_id = {segment["segment_id"]: segment for segment in segments}
    if len(by_id) != len(segments):
        return False
    for segment in segments:
        if segment["end"] <= segment["start"]:
            return False
        parent_id = segment["parent_id"]
        if parent_id is None:
            continue
        parent = by_id.get(parent_id)
        if parent is None or parent["prefix_key"] != segment["prefix_key"]:
            return False
        contains = parent["start"] <= segment["start"] and segment["end"] <= parent["end"]
        strict = parent["start"] < segment["start"] or segment["end"] < parent["end"]
        if not (contains and strict):
            return False
    children: dict = {}
    for segment in segments:
        children.setdefault(segment["parent_id"], []).append(segment)
    for kids in children.values():
        ordered = sorted(kids, key=lambda item: (item["prefix_key"], item["start"], item["end"], item["segment_id"]))
        for left, right in zip(ordered, ordered[1:]):
            if left["prefix_key"] == right["prefix_key"] and left["end"] > right["start"]:
                return False
    for segment in segments:
        seen: set[str] = set()
        cursor = segment
        while cursor["parent_id"] is not None:
            if cursor["segment_id"] in seen:
                return False
            seen.add(cursor["segment_id"])
            cursor = by_id[cursor["parent_id"]]
    return True


def split_equal(amount: int, users: list[str]) -> dict[str, int]:
    ordered = sorted(users)
    if not ordered:
        raise ValueError("SEGMENT_WITHOUT_USER")
    base, remainder = divmod(amount, len(ordered))
    shares = {user: base for user in ordered}
    for user in ordered[:remainder]:
        shares[user] += 1
    return shares


def book_for(case: dict, fixture: dict) -> dict:
    book = json.loads(json.dumps(fixture))
    override = case.get("book_override")
    if override:
        book["usd_per_million"].update(override["usd_per_million"])
    return book


def allocate_case(case: dict, fixture: dict) -> dict:
    book = book_for(case, fixture)
    incurred: dict[str, int] = {}
    lanes_priced: dict[str, dict] = {}
    for call in case["calls"]:
        for tokens in call["lanes"].values():
            if int(tokens) < 0:
                raise ValueError("LANE_NEGATIVE")
        priced, total = price_call(call["lanes"], book)
        lanes_priced[call["call_id"]] = priced
        incurred[call["call_id"]] = total

    segments = case.get("segments") or []
    if not segments_nest(segments):
        return {
            "mode": "incurred_only",
            "incurred_micro": incurred,
            "allocated_micro": dict(incurred),
        }

    pooled_from: dict[str, int] = {call_id: 0 for call_id in incurred}
    shares: dict[str, dict[str, int]] = {}
    write_micro: dict[str, int] = {}
    for segment in segments:
        writers = list(segment.get("writers") or [])
        if "write_micro_override" in segment:
            amount = int(segment["write_micro_override"])
            if len(writers) != 1:
                raise ValueError("OVERRIDE_WRITERS")
            if writers[0] not in segment["uses"]:
                raise ValueError("WRITER_NOT_IN_USES")
            incurred[writers[0]] += amount
            write_micro[segment["segment_id"]] = amount
            part = split_equal(amount, segment["uses"])
            shares[segment["segment_id"]] = part
            pooled_from[writers[0]] += amount
            continue
        lane = ROLE_TO_LANE[segment["role"]]
        holders = [call["call_id"] for call in case["calls"] if int(call["lanes"].get(lane, 0)) > 0]
        amount = sum(lanes_priced[call_id][lane] for call_id in holders)
        write_micro[segment["segment_id"]] = amount
        if len(holders) != 1:
            continue
        if holders[0] not in segment["uses"]:
            raise ValueError("WRITER_NOT_IN_USES")
        part = split_equal(amount, segment["uses"])
        shares[segment["segment_id"]] = part
        pooled_from[holders[0]] += amount

    allocated = {}
    for call_id, total in incurred.items():
        taken = pooled_from[call_id]
        private = total - taken
        received = sum(part.get(call_id, 0) for part in shares.values())
        allocated[call_id] = private + received
    return {
        "mode": "shapley",
        "incurred_micro": incurred,
        "allocated_micro": allocated,
        "write_micro": write_micro,
        "share_micro": shares,
    }
