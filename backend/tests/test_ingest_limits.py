import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import API_KEY


def _base_body():
    return {
        "customer_id": "cust_lim",
        "workflow_id": "test",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": 0.01,
        "models": {},
    }


@pytest.mark.asyncio
async def test_too_many_models_422(mock_app):
    app, _, _ = mock_app
    models = {
        f"m{i}": {"input_tokens": 1, "output_tokens": 1, "usd": 0.0}
        for i in range(51)
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={**_base_body(), "run_id": str(uuid.uuid4()), "models": models},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_nan_total_422(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={**_base_body(), "run_id": str(uuid.uuid4()), "total_usd": "NaN"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_old_ts_422(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={**_base_body(), "run_id": str(uuid.uuid4()), "ts": 1577836800},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_valid_event_202(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={**_base_body(), "run_id": str(uuid.uuid4())},
        )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_oversized_body_413(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    huge = "x" * 300_000
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            headers={"Authorization": f"Bearer {API_KEY}"},
            content=huge,
        )
    assert resp.status_code == 413
