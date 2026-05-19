from fastapi import APIRouter, Depends, Request

from ..deps import auth_workspace_by_jwt
from ..services.summary_query import fetch_summary

router = APIRouter()


@router.get("/v1/summary")
async def summary(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    return await fetch_summary(request.app.state.db, str(ws["id"]))
