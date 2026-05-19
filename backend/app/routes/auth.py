"""Magic-link auth: email a one-time code, exchange for JWT cookie."""
import logging
import secrets

import resend
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from ..auth import generate_api_key, issue_jwt
from ..config import settings
from ..deps import auth_workspace_by_jwt

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


@router.post("/v1/auth/request")
async def request_login(body: LoginRequest, request: Request):
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
        log.warning("DEV MODE — login code for %s: %s", body.email, code)

    return {"sent": True}


@router.post("/v1/auth/verify")
async def verify_login(body: VerifyRequest, request: Request, response: Response):
    redis = request.app.state.redis
    db = request.app.state.db
    expected = await redis.get(f"login:{body.email}")
    if not expected or expected != body.code:
        raise HTTPException(401, "invalid or expired code")
    await redis.delete(f"login:{body.email}")

    row = await db.fetchrow("SELECT id, name FROM workspaces WHERE email=$1", body.email)
    if not row:
        ws_id = await db.fetchval(
            """
            INSERT INTO workspaces (name, email, api_key, plan)
            VALUES ($1, $2, $3, 'free') RETURNING id
            """,
            body.email.split("@")[0],
            body.email,
            generate_api_key(),
        )
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
    """Development-only instant login (no email)."""
    if settings.environment not in ("development", "test"):
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
async def me(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    row = await request.app.state.db.fetchrow(
        "SELECT id, name, email, api_key, plan FROM workspaces WHERE id=$1",
        ws["id"],
    )
    if not row:
        raise HTTPException(401, "workspace not found")
    return dict(row)
