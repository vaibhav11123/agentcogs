import os
import tempfile
import pathlib
import pytest


@pytest.fixture(autouse=True)
def isolated_outbox(monkeypatch, tmp_path):
    """Each test gets its own outbox DB."""
    from agentcogs import outbox
    monkeypatch.setattr(outbox, "_DB_PATH", tmp_path / "outbox.db")


@pytest.fixture(autouse=True)
def do_not_star_github_from_tests(monkeypatch):
    """Tests must not call the real GitHub CLI. init() stars during setup."""
    monkeypatch.setattr("agentcogs.star.star", lambda: 0)


@pytest.fixture(autouse=True)
def sync_ingest_executor(monkeypatch):
    """Run ingest work synchronously in unit tests (no thread pool flake)."""

    class _ImmediateExecutor:
        def submit(self, fn, *args, **kwargs):
            fn()

        def shutdown(self, wait=True, cancel_futures=True):
            pass

    monkeypatch.setattr("agentcogs.client._executor", _ImmediateExecutor())


@pytest.fixture
def offline_init():
    import agentcogs
    agentcogs.init(offline=True, workspace_id="ws_test")
    yield
