"""Client watermark. The mark only moves forward."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..deps import auth_workspace_by_api_key

router = APIRouter()


class HeartbeatIn(BaseModel):
    oldest_outbox_age_sec: int


@router.post("/v1/heartbeat")
async def heartbeat(
    body: HeartbeatIn,
    request: Request,
    ws: dict = Depends(auth_workspace_by_api_key),
):
    age = max(0, min(86400, int(body.oldest_outbox_age_sec)))
    now = datetime.now(timezone.utc)
    candidate = now - timedelta(seconds=300 + age)
    db = request.app.state.db
    await db.execute(
        """
        INSERT INTO workspace_heartbeats
          (workspace_id, oldest_outbox_age_sec, watermark_event_time, recorded_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (workspace_id) DO UPDATE
        SET oldest_outbox_age_sec = EXCLUDED.oldest_outbox_age_sec,
            watermark_event_time = GREATEST(
                workspace_heartbeats.watermark_event_time,
                EXCLUDED.watermark_event_time
            ),
            recorded_at = EXCLUDED.recorded_at
        """,
        ws["id"],
        age,
        candidate,
        now,
    )
    stored = await db.fetchval(
        "SELECT watermark_event_time FROM workspace_heartbeats WHERE workspace_id = $1",
        ws["id"],
    )
    return {
        "oldest_outbox_age_sec": age,
        "watermark_event_time": stored.isoformat(),
    }
