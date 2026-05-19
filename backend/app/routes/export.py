from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from ..deps import auth_workspace_by_jwt

router = APIRouter()


@router.get("/v1/export/monthly.csv")
async def export_monthly_csv(
    year: int,
    month: int,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    rows = await request.app.state.db.fetch(
        """
        SELECT c.display_name, c.external_id,
               COALESCE(SUM(e.total_usd), 0) AS cost,
               c.monthly_revenue_usd AS rev,
               COALESCE(COUNT(e.id), 0) AS runs
        FROM customers c
        LEFT JOIN cost_events e ON e.customer_id = c.id
            AND date_trunc('month', e.ts) = make_date($2,$3,1)
        WHERE c.workspace_id = $1
        GROUP BY c.id
        ORDER BY cost DESC
        """,
        ws["id"],
        year,
        month,
    )

    def gen():
        yield "customer,external_id,ai_cost_usd,revenue_usd,gross_margin_pct,runs\n"
        for r in rows:
            cost = float(r["cost"])
            rev = float(r["rev"] or 0)
            margin = (rev - cost) / rev * 100 if rev > 0 else 0
            name = (r["display_name"] or r["external_id"]).replace('"', '""')
            yield f'"{name}",{r["external_id"]},{cost:.4f},{rev:.2f},{margin:.2f},{r["runs"]}\n'

    fname = f"agentcogs-{year}-{month:02d}.csv"
    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
