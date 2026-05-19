import pytest
import respx
from httpx import Response

import agentcogs
from agentcogs.errors import PingError


@respx.mock
def test_ping_ok():
    agentcogs.init(api_key="acg_test", workspace_id="ws_test", endpoint="http://api.test")
    respx.get("http://api.test/v1/sdk/ping").mock(
        return_value=Response(
            200,
            json={"ok": True, "workspace_id": "ws-uuid", "plan": "free", "server_time": 1},
        )
    )
    result = agentcogs.ping()
    assert result.ok is True
    assert result.workspace_id == "ws-uuid"


@respx.mock
def test_ping_invalid_key():
    agentcogs.init(api_key="bad", workspace_id="ws_test", endpoint="http://api.test")
    respx.get("http://api.test/v1/sdk/ping").mock(return_value=Response(401))
    with pytest.raises(PingError, match="Invalid API key"):
        agentcogs.ping()
