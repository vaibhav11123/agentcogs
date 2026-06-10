import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import API_KEY

INGEST_BODY = {
    "workspace_id": "ignored",
    "customer_id": "cust_pytest",
    "workflow_id": "test",
    "ts": int(time.time()),
    "status": "completed",
    "total_usd": 0.01,
    "models": {"gpt-4o-mini": {"input_tokens": 10, "output_tokens": 5, "usd": 0.01}},
}


@pytest.mark.asyncio
async def test_sdk_ping(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/sdk/ping",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "workspace_id" in data


@pytest.mark.asyncio
async def test_health(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ingest_requires_auth(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    body = {**INGEST_BODY, "run_id": str(uuid.uuid4())}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/ingest", json=body)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_with_workspace_id_ignored(mock_app):
    app, _, _ = mock_app
    run_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    def _discard_spawn(coro):
        coro.close()

    with patch("app.routes.ingest.spawn", side_effect=_discard_spawn):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/ingest",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={**INGEST_BODY, "run_id": run_id, "workspace_id": "ignored"},
            )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_ingest_without_workspace_id(mock_app):
    app, _, _ = mock_app
    run_id = str(uuid.uuid4())
    body = {k: v for k, v in INGEST_BODY.items() if k != "workspace_id"}
    transport = ASGITransport(app=app)
    def _discard_spawn(coro):
        coro.close()

    with patch("app.routes.ingest.spawn", side_effect=_discard_spawn):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/ingest",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={**body, "run_id": run_id},
            )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_ingest_and_budget(mock_app):
    """Full ingest → duplicate → budget flow with mocked DB/Redis."""
    app, mock_db, mock_redis = mock_app
    run_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)

    def _discard_spawn(coro):
        coro.close()

    with patch("app.routes.ingest.spawn", side_effect=_discard_spawn):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {API_KEY}"}

            r = await client.post(
                "/v1/ingest",
                headers=headers,
                json={**INGEST_BODY, "run_id": run_id},
            )
            assert r.status_code == 202
            assert r.json()["accepted"] is True
            assert r.json().get("duplicate") is not True

            dup = await client.post(
                "/v1/ingest",
                headers=headers,
                json={**INGEST_BODY, "run_id": run_id, "models": {}},
            )
            assert dup.status_code == 202
            assert dup.json().get("duplicate") is True

            budget = await client.get(
                "/v1/budget",
                params={"workspace": "x", "customer": "cust_pytest"},
                headers=headers,
            )

    assert budget.status_code == 200
    data = budget.json()
    assert data["status"] == "ok"
    assert data["spent_usd"] >= 0.01
    assert data["budget_usd"] == 10.0

    # Redis pipeline ran once (not on duplicate)
    mock_redis.pipeline.assert_called_once()
    pipe = mock_redis.pipeline.return_value.__aenter__.return_value
    pipe.execute.assert_awaited_once()
