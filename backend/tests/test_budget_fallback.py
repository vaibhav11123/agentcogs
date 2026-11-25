from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import redis.exceptions

from app.routes import budget as budget_route
from app.services.money import as_usd, dollars_remaining, dumps_usd, micro_to_usd
from httpx import ASGITransport, AsyncClient

from conftest import API_KEY, CUST_ID, WS_ID, _default_fetchrow


@pytest.fixture(autouse=True)
def _clear_pg_cache():
    budget_route._pg_cache.clear()
    yield
    budget_route._pg_cache.clear()


@pytest.mark.asyncio
async def test_postgres_fallback_on_redis_error(mock_app):
    app, mock_db, mock_redis = mock_app
    mock_redis.get = AsyncMock(side_effect=_redis_down_after_customer)
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
        if "settlement_receipts" in sql:
            calls["n"] += 1
            return 420_000
        if "budget_enforce" in sql:
            return False
        return None

    mock_redis.get = AsyncMock(side_effect=_redis_down_after_customer)
    mock_db.fetchval = AsyncMock(side_effect=fetchval)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"workspace": "x", "customer": "cust_pytest"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/budget", params=params, headers=headers)
        await client.get("/v1/budget", params=params, headers=headers)

    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_over_budget_is_audited_while_enforce_is_off(mock_app):
    app, mock_db, mock_redis = mock_app
    mock_redis.eval = AsyncMock(return_value=["exceeded", 9_000_000, 0])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "exceeded"
    assert body["enforce"] is False
    sqls = [str(call.args[0]) for call in mock_db.execute.await_args_list]
    assert any("budget_audit" in sql for sql in sqls)


@pytest.mark.asyncio
async def test_budget_reads_the_integer_key(mock_app):
    app, mock_db, mock_redis = mock_app

    async def get(key):
        if ":spent:" in str(key):
            return "420000"
        return None

    mock_redis.get = AsyncMock(side_effect=get)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "redis"
    assert body["spent_usd"] == 0.42
    sqls = [str(call.args[0]) for call in mock_db.fetchval.await_args_list]
    assert not any("settlement_receipts" in sql for sql in sqls)


@pytest.mark.asyncio
async def test_budget_miss_sums_receipts(mock_app):
    app, mock_db, mock_redis = mock_app
    mock_redis.get = AsyncMock(return_value=None)
    mock_db.fetchval = AsyncMock(side_effect=_fetchval_with_spend)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "postgres_fallback"
    assert body["spent_usd"] == 0.42


def test_dollar_json_uses_six_places():
    body = dumps_usd({
        "spent_usd": micro_to_usd(4200),
        "remaining_usd": dollars_remaining(as_usd("0.06"), micro_to_usd(4200)),
    })
    assert body == b'{"spent_usd":0.0042,"remaining_usd":0.0558}'


@pytest.mark.asyncio
async def test_remaining_dollars_do_not_carry_a_float_tail(mock_app):
    app, mock_db, mock_redis = mock_app

    def fetchrow(*args, **kwargs):
        sql = args[0] if args else ""
        if "monthly_budget_usd" in sql:
            return {"id": CUST_ID, "monthly_budget_usd": Decimal("0.06")}
        return _default_fetchrow(*args, **kwargs)

    async def get(key):
        if ":spent:" in str(key):
            return "4200"
        return None

    mock_db.fetchrow = AsyncMock(side_effect=fetchrow)
    mock_redis.get = AsyncMock(side_effect=get)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    raw = resp.content
    assert b'"spent_usd":0.0042' in raw
    assert b'"budget_usd":0.06' in raw
    assert b'"remaining_usd":0.0558' in raw
    assert b"999999" not in raw
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_open_budget_remaining_is_null(mock_app):
    app, mock_db, mock_redis = mock_app

    def fetchrow(*args, **kwargs):
        sql = args[0] if args else ""
        if "monthly_budget_usd" in sql:
            return {"id": CUST_ID, "monthly_budget_usd": None}
        return _default_fetchrow(*args, **kwargs)

    mock_db.fetchrow = AsyncMock(side_effect=fetchrow)
    mock_redis.get = AsyncMock(return_value=None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/budget",
            params={"workspace": "x", "customer": "cust_pytest"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    assert resp.status_code == 200
    assert b'"remaining_usd":null' in resp.content
    assert resp.json()["spent_usd"] == 0


def _redis_down_after_customer(key):
    if str(key).startswith("cust:"):
        return None
    raise redis.exceptions.ConnectionError("down")


def _fetchval_with_spend(sql, *args):
    if "settlement_receipts" in sql:
        return 420_000
    if "COUNT(*)" in sql:
        return 0
    if "INSERT INTO customers" in sql:
        return CUST_ID
    run_id = args[1] if len(args) > 1 else None
    return run_id
