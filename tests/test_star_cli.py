"""The star command uses the person's existing gh login. It does not run on import."""
import os
import stat
import subprocess
import sys

import pytest

from agentcogs.__main__ import REPO_URL, main, star

STAR_API = "/user/starred/vaibhav11123/agentcogs"


class _Completed:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_missing_gh_prints_url_and_succeeds(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("agentcogs.__main__.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "agentcogs.__main__.subprocess.run",
        lambda *args, **kwargs: calls.append(args),
    )

    assert star() == 0
    assert calls == []
    assert capsys.readouterr().out.strip() == REPO_URL


def test_logged_out_prints_url_and_does_not_call_star_api(monkeypatch, capsys):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _Completed(1, stderr="You are not logged into any GitHub hosts.")

    monkeypatch.setattr("agentcogs.__main__.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.__main__.subprocess.run", fake_run)

    assert star() == 0
    assert calls == [["/fake/gh", "auth", "status"]]
    assert capsys.readouterr().out.strip() == REPO_URL


def test_logged_in_puts_star_and_prints_result(monkeypatch, capsys):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if list(cmd[1:3]) == ["auth", "status"]:
            return _Completed(0, stderr="Logged in to github.com account person")
        return _Completed(0, stdout="")

    monkeypatch.setattr("agentcogs.__main__.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.__main__.subprocess.run", fake_run)

    assert star() == 0
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

    monkeypatch.setattr("agentcogs.__main__.shutil.which", lambda _name: "/fake/gh")
    monkeypatch.setattr("agentcogs.__main__.subprocess.run", fake_run)

    assert star() == 1
    captured = capsys.readouterr()
    assert "HTTP 401: Bad credentials" in captured.err
    assert f"Could not star {REPO_URL}" in captured.err
    assert captured.out == ""


def test_cli_star_is_the_only_path(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["agentcogs", "star"])
    monkeypatch.setattr("agentcogs.__main__.shutil.which", lambda _name: None)

    main()

    assert capsys.readouterr().out.strip() == REPO_URL


def test_cli_usage_names_star(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["agentcogs"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "python -m agentcogs outbox status" in err
    assert "python -m agentcogs star" in err


def test_outbox_status_does_not_star(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sys, "argv", ["agentcogs", "outbox", "status"])
    monkeypatch.setattr(
        "agentcogs.__main__.subprocess.run",
        lambda *args, **kwargs: calls.append(args),
    )

    main()

    assert calls == []
    assert '"pending"' in capsys.readouterr().out


def test_import_does_not_invoke_gh(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sentinel = tmp_path / "gh-was-called"
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f"echo called >> {sentinel}\n"
        "exit 0\n"
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_repo_src()), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    result = subprocess.run(
        [sys.executable, "-c", "import agentcogs"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()


def _repo_src() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
