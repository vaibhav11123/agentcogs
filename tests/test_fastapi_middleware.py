import agentcogs
from agentcogs.integrations.fastapi import AgentCOGSMiddleware
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


async def homepage(request: Request):
    import agentcogs as ac

    with ac.run(workflow_id="test"):
        pass
    return JSONResponse({"customer": ac.get_customer()})


def test_middleware_sets_customer():
    agentcogs.init(offline=True, workspace_id="ws_test")

    app = Starlette(
        routes=[Route("/", homepage)],
        middleware=[
            Middleware(
                AgentCOGSMiddleware,
                customer_id=lambda req: "tenant_from_mw",
            )
        ],
    )
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["customer"] == "tenant_from_mw"
