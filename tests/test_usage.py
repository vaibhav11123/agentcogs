import importlib
import json
import sys
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from agentcogs.__main__ import main
from agentcogs.usage import capture_usage


def _enable(monkeypatch, host=None):
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "test-project-key")
    monkeypatch.delenv("CI", raising=False)
    if host is None:
        monkeypatch.delenv("POSTHOG_HOST", raising=False)
    else:
        monkeypatch.setenv("POSTHOG_HOST", host)


def _payload(route):
    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert "test-project-key" not in str(route.calls.last.request.url)
    return body


@respx.mock
def test_unset_key_does_not_post(monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.delenv("CI", raising=False)
    capture_usage(command="outbox status", success=True)


@respx.mock
def test_blank_key_and_ci_do_not_post(monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "   ")
    monkeypatch.delenv("CI", raising=False)
    capture_usage(command="outbox status", success=True)
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "test-project-key")
    monkeypatch.setenv("CI", "true")
    capture_usage(command="outbox status", success=False)


@respx.mock
def test_capture_posts_command_version_and_outcome(monkeypatch):
    _enable(monkeypatch)
    route = respx.post("https://us.i.posthog.com/i/v0/e/").mock(return_value=Response(200))
    capture_usage(command="outbox status", success=True)
    body = _payload(route)
    assert set(body) == {"api_key", "event", "distinct_id", "properties", "timestamp"}
    assert body["api_key"] == "test-project-key"
    assert body["event"] == "product_usage"
    assert set(body["properties"]) == {
        "command",
        "package_version",
        "outcome",
        "$process_person_profile",
    }
    assert body["properties"]["command"] == "outbox status"
    assert body["properties"]["outcome"] == "success"
    assert body["properties"]["package_version"]
    assert body["properties"]["$process_person_profile"] is False
    assert "screen" not in body["properties"]


@respx.mock
def test_failure_outcome_and_custom_host(monkeypatch):
    _enable(monkeypatch, host="https://eu.i.posthog.com/capture/")
    route = respx.post("https://eu.i.posthog.com/i/v0/e/").mock(return_value=Response(400))
    capture_usage(command="unrecognized", success=False)
    body = _payload(route)
    assert body["properties"]["command"] == "unrecognized"
    assert body["properties"]["outcome"] == "failure"


@pytest.mark.parametrize(
    "command",
    ["acme", "customer name", "outbox status --key sk-test", ""],
)
@respx.mock
def test_freeform_command_is_dropped(monkeypatch, command):
    _enable(monkeypatch)
    capture_usage(command=command, success=True)


@respx.mock
def test_bad_host_and_transport_error_are_swallowed(monkeypatch):
    _enable(monkeypatch, host="https://user:secret@posthog.example")
    capture_usage(command="outbox status", success=True)
    _enable(monkeypatch, host="not a host")
    capture_usage(command="outbox status", success=True)
    _enable(monkeypatch)
    respx.post("https://us.i.posthog.com/i/v0/e/").mock(side_effect=httpx.ConnectError("down"))
    capture_usage(command="outbox status", success=False)


def test_import_does_not_post(monkeypatch):
    _enable(monkeypatch)
    with patch("httpx.post") as post:
        import agentcogs

        importlib.reload(agentcogs)
        post.assert_not_called()


@respx.mock
def test_cli_outbox_status_success(monkeypatch, capsys):
    _enable(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agentcogs", "outbox", "status", "do-not-send"])
    route = respx.post("https://us.i.posthog.com/i/v0/e/").mock(return_value=Response(200))
    main()
    body = _payload(route)
    assert body["properties"]["command"] == "outbox status"
    assert body["properties"]["outcome"] == "success"
    assert "do-not-send" not in route.calls.last.request.content.decode()
    assert "pending" in capsys.readouterr().out


@respx.mock
def test_cli_outbox_status_failure_still_raises(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agentcogs", "outbox", "status"])

    def boom():
        raise OSError("disk")

    monkeypatch.setattr("agentcogs.__main__.get_status", boom)
    route = respx.post("https://us.i.posthog.com/i/v0/e/").mock(return_value=Response(200))
    with pytest.raises(OSError, match="disk"):
        main()
    body = _payload(route)
    assert body["properties"]["outcome"] == "failure"
    assert "disk" not in route.calls.last.request.content.decode()


@respx.mock
def test_cli_unknown_command_exits_without_argv(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agentcogs", "nope", "phc_secret", "acme"])
    route = respx.post("https://us.i.posthog.com/i/v0/e/").mock(return_value=Response(200))
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    raw = route.calls.last.request.content.decode()
    assert "nope" not in raw
    assert "phc_secret" not in raw
    assert "acme" not in raw
    assert json.loads(raw)["properties"]["command"] == "unrecognized"


@respx.mock
def test_cli_without_key_makes_no_request(monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["agentcogs", "outbox", "status"])
    main()
