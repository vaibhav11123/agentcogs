from fastapi import APIRouter, Depends, HTTPException, Request
from ..deps import auth_workspace_by_jwt
from ..models import CustomerImportIn, CustomerUpdate

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


@router.post("/v1/customers/import")
async def import_customers(
    body: CustomerImportIn,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    db = request.app.state.db
    redis = request.app.state.redis

    if ws["plan"] == "free":
        count = await db.fetchval(
            "SELECT COUNT(*) FROM customers WHERE workspace_id = $1", ws["id"]
        )
        new_ids = {c.external_id for c in body.customers}
        existing = await db.fetch(
            "SELECT external_id FROM customers WHERE workspace_id = $1",
            ws["id"],
        )
        existing_ids = {r["external_id"] for r in existing}
        projected = len(existing_ids | new_ids)
        if projected > 5:
            raise HTTPException(
                402,
                f"Free tier limit (5 customers). Import would create {projected} customers.",
            )

    created = updated = 0
    errors: list[dict] = []
    for row in body.customers:
        try:
            prior = await db.fetchval(
                "SELECT id FROM customers WHERE workspace_id = $1 AND external_id = $2",
                ws["id"],
                row.external_id,
            )
            await db.execute(
                """
                INSERT INTO customers (
                    workspace_id, external_id, display_name,
                    monthly_budget_usd, monthly_revenue_usd, stripe_customer_id
                )
                VALUES ($1, $2, COALESCE($3, $2), $4, $5, $6)
                ON CONFLICT (workspace_id, external_id) DO UPDATE SET
                    display_name = COALESCE(EXCLUDED.display_name, customers.display_name),
                    monthly_budget_usd = COALESCE(
                        EXCLUDED.monthly_budget_usd, customers.monthly_budget_usd
                    ),
                    monthly_revenue_usd = COALESCE(
                        EXCLUDED.monthly_revenue_usd, customers.monthly_revenue_usd
                    ),
                    stripe_customer_id = COALESCE(
                        EXCLUDED.stripe_customer_id, customers.stripe_customer_id
                    )
                """,
                ws["id"],
                row.external_id,
                row.display_name,
                row.monthly_budget_usd,
                row.monthly_revenue_usd,
                row.stripe_customer_id,
            )
            await redis.delete(f"cust:{ws['id']}:{row.external_id}")
            if prior:
                updated += 1
            else:
                created += 1
        except Exception as e:
            errors.append({"external_id": row.external_id, "error": str(e)})

    return {"created": created, "updated": updated, "errors": errors}
