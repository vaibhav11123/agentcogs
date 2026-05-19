from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, HttpUrl
from ..deps import auth_workspace_by_jwt

router = APIRouter()


class AlertSettings(BaseModel):
    slack_webhook_url: HttpUrl | None = None
    alert_email: EmailStr | None = None


@router.patch("/v1/alerts/settings")
async def update_alert_settings(
    body: AlertSettings,
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    await request.app.state.db.execute(
        "UPDATE workspaces SET slack_webhook_url=$1, alert_email=$2 WHERE id=$3",
        str(body.slack_webhook_url) if body.slack_webhook_url else None,
        body.alert_email,
        ws["id"],
    )
    return {"ok": True}


@router.get("/v1/alerts/recent")
async def recent_anomalies(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
    limit: int = 50,
):
    rows = await request.app.state.db.fetch(
        """
        SELECT a.id, a.z_score, a.multiplier, a.mean_usd, a.created_at,
               c.id AS customer_id, c.display_name, c.external_id,
               e.total_usd, e.workflow_id, e.id AS event_id
        FROM anomalies a
        JOIN customers c ON c.id = a.customer_id
        JOIN cost_events e ON e.id = a.cost_event_id
        WHERE a.workspace_id = $1
        ORDER BY a.created_at DESC LIMIT $2
        """,
        ws["id"],
        limit,
    )
    return [dict(r) for r in rows]
