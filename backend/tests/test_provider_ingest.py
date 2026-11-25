"""A bill shaped like a mimicked OpenAI and Anthropic call is stored."""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if (not DATABASE_URL or not REDIS_URL) and not os.environ.get("GITHUB_ACTIONS"):
    pytest.skip("DATABASE_URL and REDIS_URL are required", allow_module_level=True)

from mimic_providers import ANTHROPIC_USAGE, OPENAI_USAGE
from test_ingest_calls import API_KEY, _reset

from agentcogs.provider_watch import priced_calls


@pytest.fixture
async def ledger_app():
    from app.cache import create_redis
    from app.config import settings
    from app.db import create_pool
    from app.main import app

    settings.database_url = DATABASE_URL
    settings.redis_url = REDIS_URL
    await _reset()
    app.state.db = await create_pool()
    app.state.redis = create_redis()
    yield app
    await app.state.db.close()
    await app.state.redis.aclose()


@pytest.mark.asyncio
async def test_mimicked_provider_bill_is_accepted(ledger_app):
    from httpx import ASGITransport, AsyncClient

    priced = priced_calls(
        [
            {"provider": "openai", "model": "gpt-4o-mini", "usage": OPENAI_USAGE},
            {"provider": "anthropic", "model": "claude-3-5-haiku", "usage": ANTHROPIC_USAGE},
        ]
    )
    assert priced is not None
    body = {
        "run_id": str(uuid.uuid4()),
        "customer_id": "cust_mimic",
        "workflow_id": "provider-load",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": priced["total_usd"],
        "book_id": priced["book_id"],
        "models": priced["models"],
        "calls": priced["calls"],
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    transport = ASGITransport(app=ledger_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/ingest", headers=headers, json=body)
    assert response.status_code == 202, response.text
    stored = await ledger_app.state.db.fetchrow(
        "SELECT total_usd FROM cost_events WHERE id = $1",
        body["run_id"],
    )
    assert stored is not None
    assert float(stored["total_usd"]) == priced["total_usd"]
