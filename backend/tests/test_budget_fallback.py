from unittest.mock import AsyncMock

import pytest
import redis.exceptions

from app.routes import budget as budget_route
from httpx import ASGITransport, AsyncClient

from conftest import API_KEY, CUST_ID, WS_ID


@pytest.fixture(autouse=True)
def _clear_pg_cache():
    budget_route._pg_cache.clear()
    yield
    budget_route._pg_cache.clear()


@pytest.mark.asyncio
async def test_postgres_fallback_on_redis_error(mock_app):
    app, mock_db, mock_redis = mock_app
    mock_redis.hget = AsyncMock(side_effect=redis.exceptions.ConnectionError("down"))
    mock_db.fetchval = AsyncMock(side_effect=_fetchval_with_spend)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "postgres_fallback"
    assert data["spent_usd"] == 0.42


@pytest.mark.asyncio
async def test_fallback_uses_cache(mock_app):
    app, mock_db, mock_redis = mock_app
    calls = {"n": 0}

    async def fetchval(sql, *args):
        calls["n"] += 1
        return 0.42

    mock_redis.hget = AsyncMock(side_effect=redis.exceptions.ConnectionError("down"))
    mock_db.fetchval = AsyncMock(side_effect=fetchval)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"workspace": "x", "customer": "cust_pytest"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/budget", params=params, headers=headers)
        await client.get("/v1/budget", params=params, headers=headers)

    assert calls["n"] == 1


def _fetchval_with_spend(sql, *args):
    if "SUM(total_usd)" in sql:
        return 0.42
    if "COUNT(*)" in sql:
        return 0
    if "INSERT INTO customers" in sql:
        return CUST_ID
    run_id = args[1] if len(args) > 1 else None
    return run_id
