import agentcogs
from agentcogs.config import get_config


def test_default_endpoint_is_the_local_api(monkeypatch):
    monkeypatch.delenv("AGENTCOGS_ENDPOINT", raising=False)
    agentcogs.init(api_key="acg_test", workspace_id="ws_test")
    assert get_config().endpoint == "http://localhost:8000"
