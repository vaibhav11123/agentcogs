from fastapi import APIRouter, Depends, Request
from ..deps import auth_workspace_by_jwt
from ..services.leaderboard_query import fetch_leaderboard

router = APIRouter()


@router.get("/v1/leaderboard")
async def leaderboard(
    request: Request,
    ws: dict = Depends(auth_workspace_by_jwt),
):
    return await fetch_leaderboard(request.app.state.db, str(ws["id"]))
