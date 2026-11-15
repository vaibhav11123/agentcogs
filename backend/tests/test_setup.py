import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_setup_status_hidden_outside_selfhost(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s:
        s.environment = "production"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/setup/status")
    assert resp.status_code == 200
    assert resp.json() == {"selfhost": False, "needs_setup": False}


@pytest.mark.asyncio
async def test_setup_claim_blocked_outside_selfhost(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s:
        s.environment = "production"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/setup/claim")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_setup_claim_creates_workspace_and_returns_key(mock_app):
    app, mock_db, _ = mock_app
    created = {
        "id": "00000000-0000-0000-0000-0000000000aa",
        "email": "local@localhost",
        "name": "Local",
        "api_key": "acg_live_created_key_value",
    }

    async def fetchrow(sql, *params):
        if "ORDER BY created_at" in sql:
            return None
        if "INSERT INTO workspaces" in sql:
            return created
        return None

    mock_db.fetchrow = AsyncMock(side_effect=fetchrow)
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s:
        s.environment = "selfhost"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/setup/claim")
    body = resp.json()
    assert resp.status_code == 200
    assert body["api_key"] == "acg_live_created_key_value"
    assert body["workspace_id"] == created["id"]
    assert "acg_session" in resp.cookies
