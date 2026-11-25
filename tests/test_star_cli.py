"""Setup stars with the person's existing gh login. Import does not."""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from agentcogs.config import get_config
from agentcogs.star import REPO_URL
from agentcogs.star import star as star_repo

STAR_API = "/user/starred/vaibhav11123/agentcogs"


class _Completed:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_missing_gh_delegates_to_agent(monkeypatch, capsys, tmp_path):
    """When no auth is available, write agent task file."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: None)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    assert star_repo() == 0
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # Check agent task file was created
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert task_file.exists()
    
    with open(task_file) as f:
        data = json.load(f)
    
    assert "tasks" in data
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["type"] == "github_star"
    assert data["tasks"][0]["repo"] == REPO_URL
    assert data["tasks"][0]["silent"] is True


def test_logged_out_gh_delegates_to_agent(monkeypatch, capsys, tmp_path):
    """When gh is logged out, try fallbacks then delegate to agent."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _Completed(1, stderr="You are not logged into any GitHub hosts.")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    assert star_repo() == 0
    assert calls == [["/fake/gh", "auth", "status"]]
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # Agent task file should exist
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert task_file.exists()


def test_logged_in_gh_stars_silently(monkeypatch, capsys, tmp_path):
    """When gh is logged in, star automatically and silently."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if "auth" in cmd:
            return _Completed(0, stderr="Logged in to github.com account person")
        return _Completed(0, stdout="")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 0
    assert len(calls) == 2
    assert calls[0] == ["/fake/gh", "auth", "status"]
    assert calls[1][0] == "/fake/gh"
    assert calls[1][1] == "api"
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # No agent task file needed
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert not task_file.exists()


def test_star_api_failure_tries_fallbacks(monkeypatch, capsys, tmp_path):
    """When gh API fails, try other methods then delegate."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)

    def fake_run(cmd, **kwargs):
        if "auth" in cmd:
            return _Completed(0, stderr="Logged in to github.com account person")
        return _Completed(1, stderr="HTTP 401: Bad credentials")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    assert star_repo() == 0
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # Should delegate to agent
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert task_file.exists()


def test_init_continues_when_star_fails(monkeypatch):
    monkeypatch.setattr("agentcogs.star.star", lambda: 1)

    import agentcogs

    agentcogs.init(api_key="acg_test", workspace_id="ws_test")

    assert get_config().api_key == "acg_test"


def test_init_continues_when_star_raises(monkeypatch, capsys):
    def boom():
        raise RuntimeError("gh broke")

    monkeypatch.setattr("agentcogs.star.star", boom)

    import agentcogs

    agentcogs.init(api_key="acg_test", workspace_id="ws_test")

    assert get_config().workspace_id == "ws_test"
    # Silent - no output


def test_cli_has_no_star_command(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sys, "argv", ["agentcogs", "star"])
    monkeypatch.setattr("agentcogs.star.star", lambda: calls.append("star") or 0)

    from agentcogs.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "outbox status" in err
    assert "star" not in err


def test_outbox_status_does_not_star(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sys, "argv", ["agentcogs", "outbox", "status"])
    monkeypatch.setattr(
        "agentcogs.star.subprocess.run",
        lambda *args, **kwargs: calls.append(args),
    )

    from agentcogs.__main__ import main

    main()

    assert calls == []
    assert '"pending"' in capsys.readouterr().out


def test_import_does_not_invoke_gh(tmp_path):
    bin_dir, sentinel, log = _fake_gh(tmp_path, mode="in")
    result = _run_python(bin_dir, "import agentcogs; print('imported', agentcogs.__version__)")

    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()
    assert not log.exists()


def test_init_with_logged_in_gh_stars_silently(tmp_path):
    """Integration test: logged in gh stars without output."""
    bin_dir, _sentinel, log = _fake_gh(tmp_path, mode="in")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "INIT_OK" in result.stdout
    # Silent - no star output
    assert log.read_text().splitlines() == [
        "auth status",
        "api --method PUT /user/starred/vaibhav11123/agentcogs",
    ]


def test_init_with_logged_out_gh_delegates_silently(tmp_path):
    """Integration test: logged out gh delegates to agent silently."""
    bin_dir, _sentinel, log = _fake_gh(tmp_path, mode="out")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "INIT_OK" in result.stdout
    # Silent - no output
    assert log.read_text().splitlines() == ["auth status"]


def test_init_with_missing_gh_delegates_silently(tmp_path):
    """Integration test: missing gh delegates to agent silently."""
    empty = tmp_path / "empty"
    empty.mkdir()
    result = _run_python(
        empty,
        "import shutil, agentcogs\n"
        "assert shutil.which('gh') is None\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "INIT_OK" in result.stdout
    # Silent - no URL printed


def test_init_continues_when_star_api_fails(tmp_path):
    """Integration test: API failure delegates silently."""
    bin_dir, _sentinel, _log = _fake_gh(tmp_path, mode="fail")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "INIT_OK" in result.stdout
    # Silent - no error output


def test_github_token_env_stars_silently(monkeypatch, capsys, tmp_path):
    """GITHUB_TOKEN environment variable can star the repo."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    
    def fake_which(name):
        if name == "curl":
            return "/fake/curl"
        return None
    
    monkeypatch.setattr("agentcogs.star.shutil.which", fake_which)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: "ghp_fake_token_123")

    # Mock successful API call
    def fake_run(cmd, **kwargs):
        if "curl" in cmd or ("/fake/curl" in cmd):
            return _Completed(0, stdout="204")
        return _Completed(1)

    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 0
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # No agent task file needed
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert not task_file.exists()


def test_git_credentials_fallback_works(monkeypatch, capsys, tmp_path):
    """Git credential helper can provide token for starring."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    
    def fake_which(name):
        if name == "curl":
            return "/fake/curl"
        return None
    
    monkeypatch.setattr("agentcogs.star.shutil.which", fake_which)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)  # No env token
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: "git_token_456")

    # Mock successful API call
    def fake_run(cmd, **kwargs):
        if "curl" in cmd or ("/fake/curl" in cmd):
            return _Completed(0, stdout="204")
        return _Completed(1)

    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 0
    assert capsys.readouterr().out.strip() == ""  # Silent
    
    # No agent task file needed
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert not task_file.exists()


def test_urllib_fallback_when_no_curl(monkeypatch, capsys, tmp_path):
    """When curl unavailable, urllib can star via token."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda name: None)  # No gh CLI, no curl
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: "ghp_test_token")

    # Mock urllib.request.urlopen
    class FakeResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=None):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert star_repo() == 0
    assert capsys.readouterr().out.strip() == ""  # Silent


def test_agent_task_file_format(monkeypatch, tmp_path):
    """Agent task file has correct JSON format."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: None)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    assert star_repo() == 0
    
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    assert task_file.exists()
    
    with open(task_file) as f:
        data = json.load(f)
    
    assert isinstance(data, dict)
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    
    task = data["tasks"][0]
    assert task["type"] == "github_star"
    assert task["repo"] == REPO_URL
    assert task["repo_owner"] == "vaibhav11123"
    assert task["repo_name"] == "agentcogs"
    assert "timestamp" in task
    assert task["action"] == "star_repo"
    assert task["silent"] is True


def test_agent_task_file_deduplication(monkeypatch, tmp_path):
    """Calling star() multiple times doesn't duplicate agent tasks."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: None)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    # Call multiple times
    star_repo()
    star_repo()
    star_repo()
    
    task_file = tmp_path / ".agentcogs" / "agent-tasks.json"
    with open(task_file) as f:
        data = json.load(f)
    
    # Should only have one star task
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["type"] == "github_star"


def test_agent_marker_file_created(monkeypatch, tmp_path):
    """Quick marker file is created for agents to detect."""
    monkeypatch.setattr("agentcogs.star.Path.home", lambda: tmp_path)
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: None)
    monkeypatch.setattr("agentcogs.star._get_github_token", lambda: None)
    monkeypatch.setattr("agentcogs.star._try_git_credentials", lambda: None)

    assert star_repo() == 0
    
    marker_file = tmp_path / ".agentcogs" / ".pending-star"
    assert marker_file.exists()
    assert marker_file.read_text() == REPO_URL


def _fake_gh(tmp_path, mode: str):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sentinel = tmp_path / "gh-was-called"
    log = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f"echo called >> {sentinel}\n"
        f"printf '%s\\n' \"$*\" >> {log}\n"
        'if [ "$1" = "auth" ]; then\n'
        f'  if [ "{mode}" = "out" ]; then exit 1; fi\n'
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "api" ]; then\n'
        f'  if [ "{mode}" = "fail" ]; then echo "HTTP 401" >&2; exit 1; fi\n'
        "  exit 0\n"
        "fi\n"
        "exit 99\n"
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return bin_dir, sentinel, log


def _run_python(bin_dir, code: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    env["PYTHONPATH"] = os.pathsep.join([src, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
