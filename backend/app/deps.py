from fastapi import Depends, HTTPException, Request
from .auth import verify_jwt


async def auth_workspace_by_api_key(request: Request) -> dict:
    """For SDK ingest endpoints — Bearer API key."""
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    key = header.removeprefix("Bearer ").strip()
    row = await request.app.state.db.fetchrow(
        "SELECT id, plan, name FROM workspaces WHERE api_key=$1", key
    )
    if not row:
        raise HTTPException(401, "invalid api key")
    return dict(row)


async def auth_workspace_by_jwt(request: Request) -> dict:
    """For dashboard endpoints — JWT cookie."""
    token = request.cookies.get("acg_session")
    if not token:
        raise HTTPException(401, "not authenticated")
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(401, "invalid session")
    row = await request.app.state.db.fetchrow(
        "SELECT id, plan, name, slack_webhook_url, alert_email, "
        "stripe_account_id FROM workspaces WHERE id=$1",
        payload["sub"],
    )
    if not row:
        raise HTTPException(401, "workspace not found")
    return dict(row)


async def enforce_plan_limits(
    request: Request,
    ws: dict = Depends(auth_workspace_by_api_key),
) -> dict:
    """Free tier: 5 customers max."""
    if ws["plan"] == "free":
        count = await request.app.state.db.fetchval(
            "SELECT COUNT(*) FROM customers WHERE workspace_id=$1", ws["id"]
        )
        if count >= 5:
            raise HTTPException(
                402, "Free tier limit (5 customers). Upgrade at app.agentcogs.dev"
            )
    return ws
