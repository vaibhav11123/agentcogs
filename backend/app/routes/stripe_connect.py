"""Stripe Connect — link a workspace's own Stripe account for Meter sync."""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..deps import auth_workspace_by_jwt
from ..services.stripe_mrr import subscription_monthly_usd

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
    return RedirectResponse(
        f"{settings.app_base_url.rstrip('/')}/settings?stripe=connected"
    )


@router.post("/v1/stripe/sync-revenue")
async def sync_revenue(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    """Replace typed monthly revenue with active subscription MRR."""
    if not settings.stripe_api_key:
        raise HTTPException(503, "stripe not configured")
    account = await request.app.state.db.fetchval(
        "SELECT stripe_account_id FROM workspaces WHERE id=$1",
        ws["id"],
    )
    if not account:
        raise HTTPException(400, "connect stripe before pulling revenue")

    rows = await request.app.state.db.fetch(
        """
        SELECT id, stripe_customer_id FROM customers
        WHERE workspace_id=$1 AND stripe_customer_id IS NOT NULL
        """,
        ws["id"],
    )
    updated = skipped = 0
    for row in rows:
        try:
            page = stripe.Subscription.list(
                customer=row["stripe_customer_id"],
                status="active",
                limit=100,
                stripe_account=account,
            )
            data = page["data"] if "data" in page else []
            total = sum(subscription_monthly_usd(sub) for sub in data)
        except Exception as e:
            log.warning("revenue pull failed for %s: %s", row["stripe_customer_id"], e)
            skipped += 1
            continue
        await request.app.state.db.execute(
            "UPDATE customers SET monthly_revenue_usd=$1 WHERE id=$2",
            round(total, 2),
            row["id"],
        )
        updated += 1
    return {"updated": updated, "skipped": skipped}


@router.post("/v1/stripe/disconnect")
async def disconnect(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    await request.app.state.db.execute(
        "UPDATE workspaces SET stripe_account_id=NULL WHERE id=$1",
        ws["id"],
    )
    return {"disconnected": True}
