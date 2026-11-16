"""Setup stars with the person's existing gh login. Import does not."""
import os
import stat
import subprocess
import sys

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


def test_missing_gh_prints_url_and_succeeds(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "agentcogs.star.subprocess.run",
        lambda *args, **kwargs: calls.append(args),
    )

    assert star_repo() == 0
    assert calls == []
    assert capsys.readouterr().out.strip() == REPO_URL


def test_logged_out_prints_url_and_does_not_call_star_api(monkeypatch, capsys):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _Completed(1, stderr="You are not logged into any GitHub hosts.")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 0
    assert calls == [["/fake/gh", "auth", "status"]]
    assert capsys.readouterr().out.strip() == REPO_URL


def test_logged_in_puts_star_and_prints_result(monkeypatch, capsys):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if list(cmd[1:3]) == ["auth", "status"]:
            return _Completed(0, stderr="Logged in to github.com account person")
        return _Completed(0, stdout="")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 0
    assert calls == [
        ["/fake/gh", "auth", "status"],
        ["/fake/gh", "api", "--method", "PUT", STAR_API],
    ]
    assert capsys.readouterr().out.strip() == f"Starred {REPO_URL}"


def test_star_api_failure_prints_what_happened(monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        if list(cmd[1:3]) == ["auth", "status"]:
            return _Completed(0, stderr="Logged in to github.com account person")
        return _Completed(1, stderr="HTTP 401: Bad credentials")

    monkeypatch.setattr("agentcogs.star.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.star.subprocess.run", fake_run)

    assert star_repo() == 1
    captured = capsys.readouterr()
    assert "HTTP 401: Bad credentials" in captured.out
    assert f"Could not star {REPO_URL}" in captured.out


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
    assert REPO_URL in capsys.readouterr().out


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


def test_init_with_logged_in_gh_stars_and_finishes(tmp_path):
    bin_dir, _sentinel, log = _fake_gh(tmp_path, mode="in")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "INIT_OK" in result.stdout
    assert f"Starred {REPO_URL}" in result.stdout
    assert log.read_text().splitlines() == [
        "auth status",
        "api --method PUT /user/starred/vaibhav11123/agentcogs",
    ]


def test_init_with_logged_out_gh_prints_url_and_finishes(tmp_path):
    bin_dir, _sentinel, log = _fake_gh(tmp_path, mode="out")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert REPO_URL in result.stdout
    assert "INIT_OK" in result.stdout
    assert log.read_text().splitlines() == ["auth status"]


def test_init_with_missing_gh_prints_url_and_finishes(tmp_path):
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
    assert REPO_URL in result.stdout
    assert "INIT_OK" in result.stdout


def test_init_continues_when_star_api_fails(tmp_path):
    bin_dir, _sentinel, _log = _fake_gh(tmp_path, mode="fail")
    result = _run_python(
        bin_dir,
        "import agentcogs\n"
        "agentcogs.init(offline=True, workspace_id='ws_test')\n"
        "print('INIT_OK')\n",
    )

    assert result.returncode == 0, result.stderr
    assert "Could not star" in result.stdout
    assert "INIT_OK" in result.stdout


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
