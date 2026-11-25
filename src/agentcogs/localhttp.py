"""Dashboard bound to loopback. It reads the local ledger and does not call a model."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .localstore import connect, read_credits, render_balance_html, render_dashboard


def make_server(home: Path, port: int = 3000) -> ThreadingHTTPServer:
    ledger = home

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/dashboard"}:
                body = render_dashboard(ledger).encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body)
                return
            if parsed.path == "/embed/balance":
                customer = parse_qs(parsed.query).get("customer", ["customer_001"])[0]
                conn = connect(ledger)
                try:
                    balance = read_credits(conn, customer)
                finally:
                    conn.close()
                if balance is None:
                    self._send(404, "text/plain; charset=utf-8", b"no balance")
                    return
                self._send(200, "text/html; charset=utf-8", render_balance_html(balance).encode("utf-8"))
                return
            self._send(404, "text/plain; charset=utf-8", b"not found")

        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server
