"""Read-only answers from the local ledger. A write tool is absent until the workspace allows it."""

from __future__ import annotations

import sqlite3

from .localstore import assistant_story

READ_TOOLS = ("margin_change",)


def tools() -> list[dict]:
    return [
        {
            "name": "margin_change",
            "description": "Explain a margin move from stored months. Read only.",
        }
    ]


def answer(conn: sqlite3.Connection, name: str) -> dict:
    if name not in READ_TOOLS:
        raise PermissionError("WRITE_NOT_ENABLED")
    story = assistant_story(conn)
    if story is None:
        return {"text": "Not enough months are stored to explain a margin move.", "citations": []}
    before = round(story["before"] * 100)
    after = round(story["after"] * 100)
    contributors = story["contributors"]
    scope = "most of the change" if story["scope"] == "most" else "the named rows"
    text = (
        f"Your LLM contribution margin moved from {before}% to {after}%. "
        f"Research workflow retries ${contributors['retries'] / 1_000_000:.0f}, "
        f"higher usage by Pro customers ${contributors['pro_usage'] / 1_000_000:.0f}, "
        f"and model changes ${contributors['model_changes'] / 1_000_000:.0f} "
        f"account for {scope}."
    )
    return {
        "text": text,
        "citations": [
            {"month_offset": -1, "margin": before},
            {"month_offset": 0, "margin": after, "contributors": contributors},
        ],
        "scope": story["scope"],
    }


def handle(conn: sqlite3.Connection, message: dict) -> dict:
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"serverInfo": {"name": "agentcogs-local"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools()}}
    if method == "tools/call":
        name = (message.get("params") or {}).get("name")
        try:
            result = answer(conn, name)
        except PermissionError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32001, "message": str(exc)},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "method not found"},
    }
