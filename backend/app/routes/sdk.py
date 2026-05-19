import time

from fastapi import APIRouter, Depends

from ..deps import auth_workspace_by_api_key

router = APIRouter()


@router.get("/v1/sdk/ping")
async def sdk_ping(ws: dict = Depends(auth_workspace_by_api_key)):
    return {
        "ok": True,
        "workspace_id": str(ws["id"]),
        "plan": ws["plan"],
        "server_time": int(time.time()),
    }
