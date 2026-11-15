import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, HttpUrl

from ..config import settings
from ..deps import auth_workspace_by_jwt
from ..services.alerts import slack_payload

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


@router.get("/v1/alerts/settings")
async def get_alert_settings(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    row = await request.app.state.db.fetchrow(
        "SELECT slack_webhook_url, alert_email FROM workspaces WHERE id=$1",
        ws["id"],
    )
    return {
        "slack_webhook_url": row["slack_webhook_url"] if row else None,
        "alert_email": row["alert_email"] if row else None,
    }


@router.post("/v1/alerts/test")
async def test_alert(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    """Post one sample message to the saved Slack webhook."""
    row = await request.app.state.db.fetchrow(
        "SELECT slack_webhook_url FROM workspaces WHERE id=$1",
        ws["id"],
    )
    url = row["slack_webhook_url"] if row else None
    if not url:
        raise HTTPException(400, "save a Slack webhook first")
    base = settings.app_base_url.rstrip("/")
    payload = slack_payload(
        "AgentCOGS test: cost spike alerts are connected.",
        f"{base}/settings",
        {
            "display_name": ws.get("name") or "Workspace",
            "external_id": "test",
            "workflow_id": "test",
            "total_usd": 0,
            "mean_usd": 0,
        },
    )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json=payload)
    except httpx.HTTPError as e:
        raise HTTPException(502, "could not reach the Slack webhook") from e
    if resp.status_code >= 400:
        detail = (resp.text or "Slack rejected the test message")[:200]
        raise HTTPException(502, detail)
    return {"sent": True}


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
