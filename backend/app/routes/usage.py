"""Dashboard screen beacon. The PostHog project key stays on the API."""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..usage import SCREENS, capture_screen

router = APIRouter()

_MAX_BODY = 256
_FIELDS = frozenset({"screen", "success"})


@router.post("/v1/usage", status_code=204)
async def usage(request: Request) -> Response:
    raw = await request.body()
    if len(raw) > _MAX_BODY:
        raise HTTPException(status_code=413, detail="usage body is too large")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json") from None
    if not isinstance(payload, dict) or set(payload) != _FIELDS:
        raise HTTPException(status_code=422, detail="usage accepts screen and success only")
    screen = payload["screen"]
    success = payload["success"]
    if not isinstance(screen, str) or screen not in SCREENS or not isinstance(success, bool):
        raise HTTPException(status_code=422, detail="invalid usage")
    await capture_screen(screen=screen, success=success)
    return Response(status_code=204)
