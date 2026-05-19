from fastapi import APIRouter, Depends, HTTPException, Request
from ..deps import auth_workspace_by_jwt
from ..models import CustomerUpdate

router = APIRouter()


@router.get("/v1/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    row = await request.app.state.db.fetchrow(
        "SELECT * FROM customers WHERE id=$1 AND workspace_id=$2",
        customer_id,
        ws["id"],
    )
    if not row:
        raise HTTPException(404)
    return dict(row)


@router.patch("/v1/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    updated = await request.app.state.db.fetchrow(
        """
        UPDATE customers
        SET display_name = COALESCE($3, display_name),
            monthly_budget_usd = COALESCE($4, monthly_budget_usd),
            monthly_revenue_usd = COALESCE($5, monthly_revenue_usd),
            stripe_customer_id = COALESCE($6, stripe_customer_id)
        WHERE id = $1 AND workspace_id = $2
        RETURNING *
        """,
        customer_id,
        ws["id"],
        body.display_name,
        body.monthly_budget_usd,
        body.monthly_revenue_usd,
        body.stripe_customer_id,
    )
    if not updated:
        raise HTTPException(404)
    # Invalidate budget cache.
    await request.app.state.redis.delete(f"cust:{ws['id']}:{updated['external_id']}")
    return dict(updated)
