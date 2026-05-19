"""Public demo mode — read-only views of the seeded demo workspace."""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..auth import issue_jwt
from ..config import settings
from ..services.leaderboard_query import fetch_leaderboard

router = APIRouter(prefix="/v1/demo", tags=["demo"])


def _demo_allowed() -> bool:
    return settings.demo_enabled or settings.environment in ("development", "test")


async def _demo_workspace(db) -> dict | None:
    row = await db.fetchrow(
        "SELECT id, plan, name, email FROM workspaces WHERE email=$1",
        settings.demo_workspace_email,
    )
    return dict(row) if row else None


@router.post("/session")
async def demo_session(request: Request, response: Response):
    """Issue a JWT for the demo workspace (no signup)."""
    if not _demo_allowed():
        raise HTTPException(403, "demo disabled")
    ws = await _demo_workspace(request.app.state.db)
    if not ws:
        raise HTTPException(
            404,
            f"demo workspace not found — run tools/seed_demo.sh first ({settings.demo_workspace_email})",
        )
    token = issue_jwt(str(ws["id"]), ws["email"])
    resp = JSONResponse({"ok": True, "workspace_id": str(ws["id"]), "email": ws["email"]})
    secure = settings.environment == "production"
    resp.set_cookie(
        "acg_session",
        token,
        httponly=True,
        max_age=3600,
        secure=secure,
        samesite="lax",
    )
    return resp


@router.get("/leaderboard")
async def demo_leaderboard(request: Request):
    if not _demo_allowed():
        raise HTTPException(403, "demo disabled")
    ws = await _demo_workspace(request.app.state.db)
    if not ws:
        raise HTTPException(404, "demo workspace not configured")
    return await fetch_leaderboard(request.app.state.db, str(ws["id"]))


@router.get("/alerts/recent")
async def demo_recent_alerts(request: Request, limit: int = 50):
    if not _demo_allowed():
        raise HTTPException(403, "demo disabled")
    ws = await _demo_workspace(request.app.state.db)
    if not ws:
        raise HTTPException(404, "demo workspace not configured")
    rows = await request.app.state.db.fetch(
        """
        SELECT a.id, a.z_score, a.multiplier, a.mean_usd, a.created_at,
               c.display_name, c.external_id,
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
