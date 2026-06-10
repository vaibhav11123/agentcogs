"""ASGI middleware for ingest payload limits."""
from __future__ import annotations

import json

MAX_INGEST_BYTES = 262_144


class IngestPayloadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/v1/ingest"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        cl = headers.get(b"content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_INGEST_BYTES:
                    await _send_413(send)
                    return
            except ValueError:
                pass

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            body += chunk
            more_body = message.get("more_body", False)
            if len(body) > MAX_INGEST_BYTES:
                await _send_413(send)
                return

        async def replay_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


async def _send_413(send) -> None:
    body = json.dumps({"detail": "payload too large (256KB max)"}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
