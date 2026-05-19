from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request

from ..deps import auth_workspace_by_jwt

router = APIRouter()


@router.get("/v1/installation/health")
async def installation_health(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    db = request.app.state.db
    checks = []
    state = "OK"
    message = None

    ws_row = await db.fetchrow(
        "SELECT sdk_first_seen_at, first_cost_event_at FROM workspaces WHERE id = $1",
        ws["id"],
    )
    checks.append({"name": "api_key_valid", "ok": True})

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = await db.fetchval(
        """
        SELECT COUNT(*) FROM cost_events
        WHERE workspace_id = $1 AND created_at >= $2
        """,
        ws["id"],
        since,
    )
    ingest_ok = int(recent or 0) > 0
    checks.append(
        {
            "name": "ingest_recent_24h",
            "ok": ingest_ok,
            "message": None if ingest_ok else "No cost events in the last 24 hours",
        }
    )

    if ws_row and ws_row["sdk_first_seen_at"] and not ingest_ok:
        state = "UNHEALTHY"
        message = "SDK connected but no recent usage. Verify agentcogs.run() wraps LLM calls."

    if not ws_row or not ws_row["first_cost_event_at"]:
        if state == "OK":
            state = "UNKNOWN"
            message = "Waiting for first cost event from the SDK."

    return {"state": state, "checks": checks, "message": message}
