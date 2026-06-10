"""Magic-link auth: email a one-time code, exchange for JWT cookie."""
import logging
import secrets

import resend
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from ..auth import generate_api_key, hash_api_key, issue_jwt, key_last4
from ..config import settings
from ..deps import auth_workspace_by_jwt, rate_limit_auth_relaxed, rate_limit_auth_strict

log = logging.getLogger("agentcogs.auth")
router = APIRouter()

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


class LoginRequest(BaseModel):
    email: EmailStr
    workspace_name: str | None = None


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class DevLoginIn(BaseModel):
    email: EmailStr
    name: str = "My Workspace"


def _cookie_kwargs() -> dict:
    if settings.environment == "production":
        return {"secure": True, "samesite": "lax", "domain": ".agentcogs.dev"}
    return {"secure": False, "samesite": "lax"}


async def _insert_api_key(db, workspace_id: str, api_key: str) -> None:
    await db.execute(
        """
        INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
        VALUES ($1, $2, $3)
        ON CONFLICT (key_hash) DO NOTHING
        """,
        workspace_id,
        hash_api_key(api_key),
        key_last4(api_key),
    )


@router.post("/v1/auth/request")
async def request_login(
    body: LoginRequest,
    request: Request,
    _: None = Depends(rate_limit_auth_strict),
):
    code = f"{secrets.randbelow(1_000_000):06d}"
    redis = request.app.state.redis
    await redis.setex(f"login:{body.email}", 600, code)

    if settings.resend_api_key:
        resend.Emails.send({
            "from": settings.alert_from_email,
            "to": body.email,
            "subject": "Your AgentCOGS sign-in code",
            "html": f"<p>Your code: <strong>{code}</strong></p><p>Expires in 10 minutes.</p>",
        })
    else:
        log.warning("DEV MODE — login code issued for %s", body.email)

    return {"sent": True}


@router.post("/v1/auth/verify")
async def verify_login(
    body: VerifyRequest,
    request: Request,
    response: Response,
    _: None = Depends(rate_limit_auth_strict),
):
    redis = request.app.state.redis
    db = request.app.state.db
    expected = await redis.get(f"login:{body.email}")
    if not expected or expected != body.code:
        raise HTTPException(401, "invalid or expired code")
    await redis.delete(f"login:{body.email}")

    row = await db.fetchrow("SELECT id, name FROM workspaces WHERE email=$1", body.email)
    if not row:
        api_key = generate_api_key()
        ws_id = await db.fetchval(
            """
            INSERT INTO workspaces (name, email, api_key, plan)
            VALUES ($1, $2, $3, 'free') RETURNING id
            """,
            body.email.split("@")[0],
            body.email,
            api_key,
        )
        await _insert_api_key(db, str(ws_id), api_key)
    else:
        ws_id = row["id"]

    token = issue_jwt(str(ws_id), body.email)
    response.set_cookie(
        "acg_session",
        token,
        httponly=True,
        max_age=30 * 86400,
        **_cookie_kwargs(),
    )
    return {"workspace_id": str(ws_id)}


@router.post("/v1/auth/dev-login")
async def dev_login(body: DevLoginIn, request: Request):
    """Development / self-host instant login (no email)."""
    if settings.environment not in ("development", "test", "selfhost"):
        raise HTTPException(403, "dev login disabled in production")

    db = request.app.state.db
    row = await db.fetchrow(
        "SELECT id, email, name, plan, api_key FROM workspaces WHERE email=$1",
        body.email,
    )
    if not row:
        api_key = generate_api_key()
        row = await db.fetchrow(
            """
            INSERT INTO workspaces (name, email, api_key, plan)
            VALUES ($1, $2, $3, 'free')
            RETURNING id, email, name, plan, api_key
            """,
            body.name,
            body.email,
            api_key,
        )
        await _insert_api_key(db, str(row["id"]), api_key)

    token = issue_jwt(str(row["id"]), row["email"])
    resp = JSONResponse({
        "ok": True,
        "workspace_id": str(row["id"]),
        "email": row["email"],
        "api_key": row["api_key"],
    })
    resp.set_cookie(
        "acg_session",
        token,
        httponly=True,
        max_age=30 * 86400,
        **_cookie_kwargs(),
    )
    return resp


@router.post("/v1/auth/logout")
async def logout(response: Response):
    response.delete_cookie("acg_session", **_cookie_kwargs())
    return {"ok": True}


@router.get("/v1/auth/me")
async def me(
    request: Request,
    ws: dict = Depends(rate_limit_auth_relaxed),
):
    row = await request.app.state.db.fetchrow(
        "SELECT id, name, email, plan FROM workspaces WHERE id=$1",
        ws["id"],
    )
    if not row:
        raise HTTPException(401, "workspace not found")
    key_row = await request.app.state.db.fetchrow(
        """
        SELECT key_last4, created_at
        FROM workspace_api_keys
        WHERE workspace_id = $1
          AND revoked_at IS NULL
          AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY created_at DESC
        LIMIT 1
        """,
        ws["id"],
    )
    out = dict(row)
    if key_row:
        out["key_last4"] = key_row["key_last4"]
        out["key_created_at"] = key_row["created_at"].isoformat()
    else:
        out["key_last4"] = None
        out["key_created_at"] = None
    return out


@router.post("/v1/auth/rotate-key")
async def rotate_key(
    request: Request,
    ws: dict = Depends(rate_limit_auth_relaxed),
):
    db = request.app.state.db
    new_key = generate_api_key()

    await db.execute(
        """
        UPDATE workspace_api_keys
        SET expires_at = NOW() + interval '24 hours'
        WHERE workspace_id = $1
          AND revoked_at IS NULL
          AND (expires_at IS NULL OR expires_at > NOW())
          AND key_hash != $2
        """,
        ws["id"],
        hash_api_key(new_key),
    )

    await db.execute(
        """
        INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
        VALUES ($1, $2, $3)
        """,
        ws["id"],
        hash_api_key(new_key),
        key_last4(new_key),
    )

    await db.execute(
        "UPDATE workspaces SET api_key = $1 WHERE id = $2",
        new_key,
        ws["id"],
    )

    expire_row = await db.fetchrow(
        """
        SELECT MIN(expires_at) AS old_keys_expire_at
        FROM workspace_api_keys
        WHERE workspace_id = $1
          AND expires_at IS NOT NULL
          AND expires_at > NOW()
          AND key_hash != $2
        """,
        ws["id"],
        hash_api_key(new_key),
    )
    old_expire = expire_row["old_keys_expire_at"] if expire_row else None

    return {
        "api_key": new_key,
        "old_keys_expire_at": old_expire.isoformat() if old_expire else None,
    }
