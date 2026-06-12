from fastapi import Depends, HTTPException, Request

from .auth import hash_api_key, verify_jwt
from .config import settings
from .ratelimit import check_rate


async def auth_workspace_by_api_key(request: Request) -> dict:
    """For SDK ingest endpoints — Bearer API key (hashed lookup)."""
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    key = header.removeprefix("Bearer ").strip()
    key_hash = hash_api_key(key)
    row = await request.app.state.db.fetchrow(
        """
        SELECT w.id, w.plan, w.name
        FROM workspace_api_keys k
        JOIN workspaces w ON w.id = k.workspace_id
        WHERE k.key_hash = $1
          AND k.revoked_at IS NULL
          AND (k.expires_at IS NULL OR k.expires_at > NOW())
        """,
        key_hash,
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


def client_ip(request: Request) -> str:
    if settings.environment == "production":
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def rate_limit_ingest(request: Request, ws: dict = Depends(enforce_plan_limits)) -> dict:
    allowed, retry_after = await check_rate(
        request.app.state.redis,
        f"rl:ingest:ws:{ws['id']}",
        limit=1000,
        window_s=60,
    )
    if not allowed:
        raise HTTPException(
            429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return ws


async def rate_limit_auth_strict(request: Request) -> None:
    ip = client_ip(request)
    allowed, retry_after = await check_rate(
        request.app.state.redis,
        f"rl:auth:strict:{ip}",
        limit=10,
        window_s=60,
    )
    if not allowed:
        raise HTTPException(
            429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_auth_relaxed(request: Request, ws: dict = Depends(auth_workspace_by_jwt)) -> dict:
    ip = client_ip(request)
    allowed, retry_after = await check_rate(
        request.app.state.redis,
        f"rl:auth:relaxed:{ip}",
        limit=60,
        window_s=60,
    )
    if not allowed:
        raise HTTPException(
            429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return ws
