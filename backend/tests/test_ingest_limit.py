"""The ingest body limit must give up when the client goes away."""

import pytest

from app.middleware import IngestPayloadLimitMiddleware


@pytest.mark.asyncio
async def test_disconnect_while_reading_does_not_read_again():
    reads = {"n": 0}
    messages = [
        {"type": "http.request", "body": b"{", "more_body": True},
        {"type": "http.disconnect"},
    ]

    async def receive():
        reads["n"] += 1
        if not messages:
            raise AssertionError("receive called after the client disconnected")
        return messages.pop(0)

    sent = []

    async def send(message):
        sent.append(message)

    reached = []

    async def app(scope, receive, send):
        reached.append(scope["path"])

    await IngestPayloadLimitMiddleware(app)(
        {"type": "http", "path": "/v1/ingest", "headers": []},
        receive,
        send,
    )
    assert reads["n"] == 2
    assert reached == []
    assert sent == []


@pytest.mark.asyncio
async def test_a_finished_body_is_replayed_once():
    messages = [{"type": "http.request", "body": b"{}", "more_body": False}]

    async def receive():
        if not messages:
            raise AssertionError("body was read twice")
        return messages.pop(0)

    seen = {}

    async def app(scope, receive, send):
        seen["message"] = await receive()

    async def send(message):
        return None

    await IngestPayloadLimitMiddleware(app)(
        {"type": "http", "path": "/v1/ingest", "headers": []},
        receive,
        send,
    )
    assert seen["message"]["body"] == b"{}"
    assert seen["message"]["more_body"] is False
