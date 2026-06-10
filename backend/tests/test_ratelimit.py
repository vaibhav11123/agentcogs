import time
import uuid
from unittest.mock import AsyncMock

import pytest
import redis.exceptions
from httpx import ASGITransport, AsyncClient

from app.ratelimit import check_rate
from conftest import API_KEY, WS_ID


@pytest.mark.asyncio
async def test_ingest_rate_limit_429(mock_app, monkeypatch):
    """Window limit enforced (uses limit=2 here for speed; production limit is 1000/min)."""
    from app import deps

    app, _, mock_redis = mock_app
    n = {"v": 0}

    async def incr(key):
        n["v"] += 1
        return n["v"]

    mock_redis.incr = AsyncMock(side_effect=incr)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.ttl = AsyncMock(return_value=30)

    real_check = deps.check_rate

    async def fast_ingest_limit(redis, bucket, limit, window_s):
        if bucket.startswith("rl:ingest"):
            limit = 2
        return await real_check(redis, bucket, limit, window_s)

    monkeypatch.setattr(deps, "check_rate", fast_ingest_limit)

    transport = ASGITransport(app=app)
    body = {
        "workspace_id": "ignored",
        "customer_id": "cust_rl",
        "workflow_id": "w",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": 0.01,
        "models": {},
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(2):
            r = await client.post(
                "/v1/ingest",
                headers=headers,
                json={**body, "run_id": str(uuid.uuid4())},
            )
            assert r.status_code == 202
        blocked = await client.post(
            "/v1/ingest",
            headers=headers,
            json={**body, "run_id": str(uuid.uuid4())},
        )
    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after")


@pytest.mark.asyncio
async def test_redis_down_fail_open():
    import redis as redis_lib

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=redis_lib.exceptions.ConnectionError("down"))
    allowed, retry = await check_rate(mock_redis, "b", 1, 60)
    assert allowed is True
    assert retry == 0
