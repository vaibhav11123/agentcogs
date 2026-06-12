import httpx
import respx

from agentcogs.client import emit_event_sync, reset_client
from agentcogs.outbox import clear_outbox, outbox_size


def test_429_enqueues_then_drains():
    import agentcogs

    agentcogs.init(
        api_key="acg_live_test",
        workspace_id="ws",
        endpoint="http://testserver",
    )
    reset_client()
    clear_outbox()

    event = {
        "run_id": "00000000-0000-0000-0000-00000000a099",
        "customer_id": "c",
        "workflow_id": "w",
        "ts": 1,
        "status": "completed",
        "total_usd": 0.01,
        "models": {},
    }

    with respx.mock:
        route = respx.post("http://testserver/v1/ingest").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "1"}),
                httpx.Response(202, json={"accepted": True}),
                httpx.Response(202, json={"accepted": True}),
            ]
        )
        ok, err = emit_event_sync(event)
        assert ok is False
        assert outbox_size() == 1

        ok2, err2 = emit_event_sync(event)
        assert ok2 is True
        assert outbox_size() == 0
        assert route.call_count >= 2

    reset_client()
    clear_outbox()
