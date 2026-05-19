import os
import tempfile
import pathlib
import pytest


@pytest.fixture(autouse=True)
def isolated_outbox(monkeypatch, tmp_path):
    """Each test gets its own outbox DB."""
    from agentcogs import outbox
    monkeypatch.setattr(outbox, "_DB_PATH", tmp_path / "outbox.db")


@pytest.fixture
def offline_init():
    import agentcogs
    agentcogs.init(offline=True, workspace_id="ws_test")
    yield
