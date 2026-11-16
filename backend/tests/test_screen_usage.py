import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.usage import PACKAGE_VERSION, SCREENS, capture_screen
from httpx import ASGITransport, AsyncClient


def _enable(monkeypatch, host=None):
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "test-project-key")
    monkeypatch.delenv("CI", raising=False)
    if host is None:
        monkeypatch.delenv("POSTHOG_HOST", raising=False)
    else:
        monkeypatch.setenv("POSTHOG_HOST", host)


class _Client:
    def __init__(self, *args, **kwargs):
        self.calls = kwargs.pop("calls")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, json=None):
        self.calls.append((url, json))

        class _Response:
            status_code = 200

        return _Response()


def _factory(calls):
    def build(*args, **kwargs):
        kwargs["calls"] = calls
        return _Client(*args, **kwargs)

    return build


@pytest.mark.asyncio
async def test_usage_posts_screen_version_and_outcome(mock_app, monkeypatch):
    _enable(monkeypatch)
    app, _, _ = mock_app
    calls = []
    transport = ASGITransport(app=app)
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/usage", json={"screen": "alerts", "success": False})
    assert resp.status_code == 204
    assert resp.content == b""
    assert len(calls) == 1
    url, body = calls[0]
    assert url == "https://us.i.posthog.com/i/v0/e/"
    assert body["api_key"] == "test-project-key"
    assert body["event"] == "product_usage"
    assert set(body["properties"]) == {
        "screen",
        "package_version",
        "outcome",
        "$process_person_profile",
    }
    assert body["properties"]["screen"] == "alerts"
    assert body["properties"]["outcome"] == "failure"
    assert body["properties"]["package_version"] == PACKAGE_VERSION
    assert body["properties"]["$process_person_profile"] is False
    assert "command" not in body["properties"]
    raw = json.dumps(body["properties"])
    assert "test-project-key" not in raw


@pytest.mark.asyncio
async def test_usage_without_key_does_not_post(mock_app, monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.delenv("CI", raising=False)
    app, _, _ = mock_app
    calls = []
    transport = ASGITransport(app=app)
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/usage", json={"screen": "customers", "success": True})
    assert resp.status_code == 204
    assert calls == []


@pytest.mark.asyncio
async def test_ci_skips_post(mock_app, monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "test-project-key")
    monkeypatch.setenv("CI", "true")
    app, _, _ = mock_app
    calls = []
    transport = ASGITransport(app=app)
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/usage", json={"screen": "login", "success": True})
    assert resp.status_code == 204
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"screen": "customer", "success": True, "customer": "Acme"},
        {"screen": "settings", "success": True, "amount": 12.5},
        {"screen": "login", "success": True, "api_key": "acg_live_secret"},
        {"screen": "onboarding", "success": True, "prompt": "hello"},
        {"screen": "customers/acme", "success": True},
        {"screen": "customer", "success": "yes"},
        {"success": True},
        {"screen": "alerts"},
    ],
)
async def test_usage_rejects_extra_or_unknown_fields(mock_app, monkeypatch, payload):
    _enable(monkeypatch)
    app, _, _ = mock_app
    calls = []
    transport = ASGITransport(app=app)
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/usage", json=payload)
    assert resp.status_code == 422
    assert calls == []
    text = resp.text.lower()
    assert "acme" not in text
    assert "acg_live_secret" not in text
    assert "hello" not in text


@pytest.mark.asyncio
async def test_usage_rejects_a_large_body(mock_app, monkeypatch):
    _enable(monkeypatch)
    app, _, _ = mock_app
    calls = []
    transport = ASGITransport(app=app)
    body = json.dumps({"screen": "login", "success": True, "pad": "x" * 400})
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/usage",
                content=body,
                headers={"Content-Type": "application/json"},
            )
    assert resp.status_code == 413
    assert calls == []


@pytest.mark.asyncio
async def test_posthog_outage_still_returns_204(mock_app, monkeypatch):
    _enable(monkeypatch, host="https://eu.i.posthog.com")

    class _Down:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json=None):
            raise RuntimeError(f"down {json['api_key']} {url}")

    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    with patch("app.usage.httpx.AsyncClient", _Down):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/usage", json={"screen": "customer", "success": True})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_capture_screen_drops_unknown_names(monkeypatch):
    _enable(monkeypatch)
    calls = []
    with patch("app.usage.httpx.AsyncClient", _factory(calls)):
        await capture_screen(screen="customers/acme", success=True)
        await capture_screen(screen="customer", success=True)
    assert len(calls) == 1
    assert calls[0][1]["properties"]["screen"] == "customer"


def test_screen_names_match_the_dashboard():
    text = (Path(__file__).resolve().parents[2] / "dashboard" / "src" / "lib" / "usage.ts").read_text()
    for name in sorted(SCREENS):
        assert f'"{name}"' in text
    assert "customer_id" not in text
    assert "JSON.stringify({ screen, success })" in text
    assert "isSample()" in text
