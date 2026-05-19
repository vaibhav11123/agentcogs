"""Stripe Connect — link a workspace's own Stripe account for Meter sync."""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..deps import auth_workspace_by_jwt

log = logging.getLogger("agentcogs.stripe_connect")
router = APIRouter()

if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key


@router.get("/v1/stripe/status")
async def status(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    row = await request.app.state.db.fetchrow(
        "SELECT stripe_account_id FROM workspaces WHERE id=$1",
        ws["id"],
    )
    return {
        "connected": bool(row and row["stripe_account_id"]),
        "account_id": row["stripe_account_id"] if row else None,
    }


@router.get("/v1/stripe/oauth/start")
async def oauth_start(ws: dict = Depends(auth_workspace_by_jwt)):
    if not settings.stripe_connect_client_id:
        raise HTTPException(500, "stripe connect not configured")
    url = (
        "https://connect.stripe.com/oauth/authorize"
        f"?response_type=code&client_id={settings.stripe_connect_client_id}"
        f"&scope=read_write&state={ws['id']}"
    )
    return {"url": url}


@router.get("/v1/stripe/oauth/callback")
async def oauth_callback(code: str, state: str, request: Request):
    if not settings.stripe_api_key:
        raise HTTPException(503, "stripe not configured")
    try:
        resp = stripe.OAuth.token(grant_type="authorization_code", code=code)
    except Exception as e:
        log.exception("stripe oauth token exchange failed: %s", e)
        raise HTTPException(400, "oauth exchange failed")

    await request.app.state.db.execute(
        "UPDATE workspaces SET stripe_account_id=$1 WHERE id=$2",
        resp["stripe_user_id"],
        state,
    )
    return RedirectResponse("https://app.agentcogs.dev/settings?stripe=connected")


@router.post("/v1/stripe/disconnect")
async def disconnect(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    await request.app.state.db.execute(
        "UPDATE workspaces SET stripe_account_id=NULL WHERE id=$1",
        ws["id"],
    )
    return {"disconnected": True}
