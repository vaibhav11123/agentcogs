"""Shared fixtures for backend API tests."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth import hash_api_key

WS_ID = "00000000-0000-0000-0000-00000000a001"
CUST_ID = "00000000-0000-0000-0000-00000000c001"
API_KEY = "acg_live_TESTKEY"
API_KEY_HASH = hash_api_key(API_KEY)


@pytest.fixture
def mock_app():
    """FastAPI app with mocked asyncpg pool + Redis (no Docker required)."""
    from app.main import app

    mock_db = AsyncMock()
    mock_redis = MagicMock()

    pipe = MagicMock()
    pipe.hincrbyfloat = MagicMock(return_value=pipe)
    pipe.hincrby = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=None)
    mock_redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe)
    mock_redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.hget = AsyncMock(return_value="0.01")
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.ttl = AsyncMock(return_value=60)

    mock_db.fetchrow = AsyncMock(side_effect=_default_fetchrow)
    mock_db.fetchval = AsyncMock(side_effect=_default_fetchval)
    mock_db.execute = AsyncMock(return_value="OK")

    app.state.db = mock_db
    app.state.redis = mock_redis
    return app, mock_db, mock_redis


def _default_fetchrow(*args, **kwargs):
    sql = args[0] if args else ""
    if "workspace_api_keys" in sql and "key_hash" in sql:
        if len(args) > 1 and args[1] == API_KEY_HASH:
            return {"id": WS_ID, "plan": "free", "name": "Test Co"}
        return None
    if "monthly_budget_usd" in sql:
        return {"id": CUST_ID, "monthly_budget_usd": Decimal("10.0000")}
    if "FROM workspaces WHERE id" in sql and "api_key" not in sql.lower():
        return {"id": WS_ID, "name": "Test Co", "email": "t@test.com", "plan": "free"}
    if "workspace_api_keys" in sql and "key_last4" in sql:
        return {"key_last4": "TKEY", "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)}
    return None


_inserted_run_ids: set[str] = set()


def _default_fetchval(*args, **kwargs):
    sql = args[0] if args else ""
    if "COUNT(*)" in sql:
        return 0
    if "INSERT INTO customers" in sql:
        return CUST_ID
    if "INSERT INTO cost_events" in sql:
        run_id = args[1] if len(args) > 1 else None
        if run_id in _inserted_run_ids:
            return None
        _inserted_run_ids.add(run_id)
        return run_id
    return None


@pytest.fixture(autouse=True)
def _clear_inserted_runs():
    _inserted_run_ids.clear()
    yield
    _inserted_run_ids.clear()
