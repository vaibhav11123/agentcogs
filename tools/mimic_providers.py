#!/usr/bin/env python3
"""Local stand-ins for the paid OpenAI, Anthropic, and Stripe APIs.

Nothing here calls a provider. The official SDKs point at this process.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

OPENAI_USAGE = {
    "prompt_tokens": 12000,
    "completion_tokens": 20,
    "total_tokens": 12020,
    "prompt_tokens_details": {"cached_tokens": 4000, "cache_write_tokens": 3000},
    "completion_tokens_details": {"reasoning_tokens": 5},
}

ANTHROPIC_USAGE = {
    "input_tokens": 500,
    "output_tokens": 20,
    "cache_read_input_tokens": 8000,
    "cache_creation_input_tokens": 200,
    "cache_creation": {"ephemeral_5m_input_tokens": 120, "ephemeral_1h_input_tokens": 80},
}

# Quantity 2 at $50, half off, plus a metered price that must not count.
STRIPE_SUBSCRIPTION = {
    "id": "sub_mock",
    "object": "subscription",
    "status": "active",
    "customer": "cus_mock",
    "discount": {"coupon": {"percent_off": 50, "valid": True, "amount_off": None}},
    "items": {
        "object": "list",
        "data": [
            {
                "id": "si_licensed",
                "object": "subscription_item",
                "quantity": 2,
                "price": {
                    "id": "price_licensed",
                    "object": "price",
                    "unit_amount": 5000,
                    "recurring": {
                        "interval": "month",
                        "interval_count": 1,
                        "usage_type": "licensed",
                    },
                },
            },
            {
                "id": "si_metered",
                "object": "subscription_item",
                "quantity": 1,
                "price": {
                    "id": "price_metered",
                    "object": "price",
                    "unit_amount": 1,
                    "recurring": {
                        "interval": "month",
                        "interval_count": 1,
                        "usage_type": "metered",
                    },
                },
            },
        ],
    },
}


class ProviderMimic(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        super().__init__((host, port), _Handler)
        self.ingests: list[dict] = []
        self.meters: set[str] = set()
        self.counts = {"openai": 0, "anthropic": 0, "stripe_list": 0, "stripe_meter": 0}
        self.lock = threading.Lock()

    @property
    def origin(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def handle_error(self, request, client_address) -> None:
        # Clients close the stream as soon as the last chunk arrives.
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        server: ProviderMimic = self.server  # type: ignore[assignment]
        if path == "/v1/budget":
            self._json(
                {
                    "status": "ok",
                    "spent_usd": 0,
                    "budget_usd": None,
                    "remaining_usd": None,
                    "enforce": False,
                    "decision": "ok",
                }
            )
            return
        if path == "/v1/subscriptions":
            with server.lock:
                server.counts["stripe_list"] += 1
            self._json(
                {
                    "object": "list",
                    "url": "/v1/subscriptions",
                    "has_more": False,
                    "data": [STRIPE_SUBSCRIPTION],
                }
            )
            return
        self._json({"error": {"message": f"no route {path}"}}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = _parse_body(raw, self.headers.get("Content-Type", ""))
        server: ProviderMimic = self.server  # type: ignore[assignment]
        if path == "/v1/chat/completions":
            with server.lock:
                server.counts["openai"] += 1
            model = str(body.get("model") or "gpt-4o-mini")
            if body.get("stream") is True or body.get("stream") == "true":
                self._openai_stream(model)
            else:
                self._json(_openai_message(model))
            return
        if path == "/v1/messages":
            with server.lock:
                server.counts["anthropic"] += 1
            model = str(body.get("model") or "claude-3-5-haiku")
            self._json(_anthropic_message(model))
            return
        if path == "/v1/billing/meter_events":
            identifier = str(body.get("identifier") or "")
            with server.lock:
                server.counts["stripe_meter"] += 1
                duplicate = identifier in server.meters
                server.meters.add(identifier)
            if duplicate:
                self._json(
                    {
                        "error": {
                            "type": "invalid_request_error",
                            "message": f"An event with identifier {identifier} was already submitted.",
                        }
                    },
                    status=400,
                )
                return
            self._json(
                {
                    "object": "billing.meter_event",
                    "identifier": identifier,
                    "event_name": body.get("event_name"),
                    "created": 1,
                    "livemode": False,
                    "payload": body.get("payload") or {},
                    "timestamp": 1,
                }
            )
            return
        if path == "/v1/ingest":
            with server.lock:
                server.ingests.append(body)
            self._json({"accepted": True}, status=202)
            return
        self._json({"error": {"message": f"no route {path}"}}, status=404)

    def _openai_stream(self, model: str) -> None:
        usage = dict(OPENAI_USAGE)
        chunks = [
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": "ok"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [],
                "usage": usage,
            },
        ]
        payload = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        payload += "data: [DONE]\n\n"
        encoded = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _parse_body(raw: bytes, content_type: str) -> dict:
    if not raw:
        return {}
    if "application/json" in content_type:
        return json.loads(raw.decode() or "{}")
    from urllib.parse import parse_qs

    parsed = parse_qs(raw.decode(), keep_blank_values=True)
    flat: dict = {}
    for key, values in parsed.items():
        _assign(flat, key, values[0] if len(values) == 1 else values)
    return flat


def _assign(target: dict, key: str, value: str) -> None:
    # Stripe posts payload[stripe_customer_id]=cus_x
    parts = key.replace("]", "").split("[")
    cursor = target
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def _openai_message(model: str) -> dict:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": OPENAI_USAGE,
    }


def _anthropic_message(model: str) -> dict:
    return {
        "id": "msg_mock",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": ANTHROPIC_USAGE,
    }


def serve(host: str = "127.0.0.1", port: int = 8766) -> None:
    server = ProviderMimic(host, port)
    print(f"mimic {server.origin}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
