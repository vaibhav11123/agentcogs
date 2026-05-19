"""AgentCOGS's own subscription billing (Stripe Checkout)."""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..deps import auth_workspace_by_jwt

log = logging.getLogger("agentcogs.billing")
router = APIRouter()

if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key

PLANS = {
    "starter": {"price_id": "price_STARTER_REPLACE_ME", "customer_cap": 50},
    "growth": {"price_id": "price_GROWTH_REPLACE_ME", "customer_cap": None},
}


class CheckoutIn(BaseModel):
    plan: str


@router.get("/v1/billing/status")
async def billing_status(ws: dict = Depends(auth_workspace_by_jwt)):
    cap = PLANS.get(ws["plan"], {}).get("customer_cap", 5)
    return {"plan": ws["plan"], "customer_cap": cap}


@router.post("/v1/billing/checkout")
async def create_checkout(
    body: CheckoutIn,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    if not settings.stripe_api_key:
        raise HTTPException(503, "billing not configured")
    if body.plan not in PLANS:
        raise HTTPException(400, "unknown plan")
    sess = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": PLANS[body.plan]["price_id"], "quantity": 1}],
        success_url=f"{settings.app_base_url.rstrip('/')}/settings?upgraded=1",
        cancel_url=f"{settings.app_base_url.rstrip('/')}/settings",
        client_reference_id=str(ws["id"]),
        metadata={"workspace_id": str(ws["id"]), "plan": body.plan},
    )
    return {"url": sess.url}


@router.post("/v1/billing/portal")
async def billing_portal(request: Request, ws: dict = Depends(auth_workspace_by_jwt)):
    if not settings.stripe_api_key:
        raise HTTPException(503, "billing not configured")
    row = await request.app.state.db.fetchrow(
        "SELECT stripe_customer_id FROM workspaces WHERE id=$1",
        ws["id"],
    )
    if not row or not row["stripe_customer_id"]:
        raise HTTPException(400, "no stripe customer yet — upgrade first")
    sess = stripe.billing_portal.Session.create(
        customer=row["stripe_customer_id"],
        return_url=f"{settings.app_base_url.rstrip('/')}/settings",
    )
    return {"url": sess.url}


@router.post("/v1/billing/webhook")
async def webhook(request: Request):
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, "webhook not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig,
            settings.stripe_webhook_secret,
        )
    except Exception as e:
        log.warning("invalid stripe signature: %s", e)
        raise HTTPException(400, "invalid signature")

    db = request.app.state.db
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        ws_id = obj.get("metadata", {}).get("workspace_id")
        plan = obj.get("metadata", {}).get("plan")
        customer_id = obj.get("customer")
        if ws_id and plan:
            await db.execute(
                "UPDATE workspaces SET plan=$1, stripe_customer_id=$2 WHERE id=$3",
                plan,
                customer_id,
                ws_id,
            )
            log.info("workspace %s upgraded to %s", ws_id, plan)

    elif etype == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        await db.execute(
            "UPDATE workspaces SET plan='free' WHERE stripe_customer_id=$1",
            customer_id,
        )
        log.info("workspace downgraded to free, stripe_customer=%s", customer_id)

    return {"received": True}
