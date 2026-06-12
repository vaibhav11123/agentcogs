import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_dev_login_allowed_in_development(mock_app):
    from app.auth import generate_api_key

    app, mock_db, _ = mock_app

    async def fetchrow(sql, *params):
        if "FROM workspaces WHERE email" in sql:
            return None
        if "RETURNING id, email" in sql:
            key = generate_api_key()
            return {
                "id": "00000000-0000-0000-0000-00000000d001",
                "email": params[1],
                "name": params[0],
                "plan": "free",
                "api_key": key,
            }
        return None

    mock_db.fetchrow = AsyncMock(side_effect=fetchrow)
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s:
        s.environment = "development"
        s.resend_api_key = ""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/auth/dev-login",
                json={"email": "dev@test.com", "name": "Dev"},
            )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dev_login_blocked_in_production(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s:
        s.environment = "production"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/auth/dev-login",
                json={"email": "dev@test.com", "name": "Dev"},
            )
    assert resp.status_code == 403
