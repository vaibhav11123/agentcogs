import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .config import settings
from .db import create_pool
from .cache import create_redis
from fastapi import Request

from .routes import (
    ingest,
    budget,
    customers,
    leaderboard,
    events,
    alerts,
    billing,
    stripe_connect,
    export,
    auth,
    demo,
    summary,
    sdk,
    onboarding,
    installation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await create_pool()
    app.state.redis = create_redis()
    logging.info("agentcogs backend started, env=%s", settings.environment)
    yield
    await app.state.db.close()
    await app.state.redis.aclose()


app = FastAPI(
    title="AgentCOGS API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(request: Request):
    checks = {}
    ok = True
    try:
        await request.app.state.db.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)
        ok = False
    try:
        pong = await request.app.state.redis.ping()
        checks["redis"] = "ok" if pong else "fail"
        if not pong:
            ok = False
    except Exception as e:
        checks["redis"] = str(e)
        ok = False
    from fastapi.responses import JSONResponse

    body = {"status": "ready" if ok else "degraded", "checks": checks}
    return JSONResponse(body, status_code=200 if ok else 503)


app.include_router(ingest.router, tags=["ingest"])
app.include_router(sdk.router, tags=["sdk"])
app.include_router(onboarding.router, tags=["onboarding"])
app.include_router(installation.router, tags=["installation"])
app.include_router(budget.router, tags=["budget"])
app.include_router(customers.router, tags=["customers"])
app.include_router(leaderboard.router, tags=["dashboard"])
app.include_router(summary.router, tags=["dashboard"])
app.include_router(events.router, tags=["dashboard"])
app.include_router(alerts.router, tags=["alerts"])
app.include_router(billing.router, tags=["billing"])
app.include_router(stripe_connect.router, tags=["stripe"])
app.include_router(export.router, tags=["export"])
app.include_router(auth.router, tags=["auth"])
app.include_router(demo.router)
