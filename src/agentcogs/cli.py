"""Local commands. `python -m agentcogs outbox status` stays the offline outbox check."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import localstore
from .outbox import get_status
from .reports import recommended_budget_micro, regression_comment, warning_micro


def home_from_env() -> Path:
    raw = os.environ.get("AGENTCOGS_HOME")
    if raw:
        return Path(raw)
    return Path.cwd() / ".agentcogs"


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "outbox" and args[1] == "status":
        print(json.dumps(get_status(), indent=2))
        return
    if not args or args[0] in {"-h", "--help", "help"}:
        _usage()
        return
    command, rest = args[0], args[1:]
    commands = {
        "init": _init,
        "doctor": _doctor,
        "status": _status,
        "verify": _verify,
        "export": _export,
        "backup": _backup,
        "restore": _restore,
        "update": _update,
        "demo": _demo,
        "ci": _ci,
        "budget": _budget,
        "start": _start,
        "stop": _stop,
    }
    handler = commands.get(command)
    if handler is None:
        print("Usage: python -m agentcogs outbox status", file=sys.stderr)
        raise SystemExit(1)
    handler(rest)


def _usage() -> None:
    print(
        "agentcogs init | doctor | status | verify | export | backup | restore | update | demo | ci | budget"
    )


def _init(rest: list[str]) -> None:
    exist_ok = "--yes" in rest
    home = home_from_env()
    try:
        info = localstore.init_home(home, exist_ok=exist_ok)
    except FileExistsError:
        print(f"Ledger already exists at {home / 'ledger.sqlite'}. Re-run with --yes to keep it.", file=sys.stderr)
        raise SystemExit(2) from None
    if info["events"] == 0:
        localstore.verify_fixture(home)
        info = localstore.export_json(home)["status"]
    print(json.dumps({"ready": True, "home": str(home), **info}))


def _doctor(_rest: list[str]) -> None:
    problems = localstore.doctor(home_from_env())
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("ok")


def _status(_rest: list[str]) -> None:
    conn = localstore.connect(home_from_env())
    try:
        print(json.dumps(localstore.status(conn)))
    finally:
        conn.close()


def _verify(_rest: list[str]) -> None:
    result = localstore.verify_fixture(home_from_env())
    print(json.dumps(result))


def _export(rest: list[str]) -> None:
    payload = localstore.export_json(home_from_env())
    if rest:
        Path(rest[0]).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(rest[0])
        return
    print(json.dumps(payload))


def _backup(rest: list[str]) -> None:
    if not rest:
        dest = localstore.prepare_migration(home_from_env())
    else:
        dest = localstore.backup_database(home_from_env(), Path(rest[0]))
    print(dest)


def _restore(rest: list[str]) -> None:
    if not rest:
        print("Usage: agentcogs restore <file> [--yes]", file=sys.stderr)
        raise SystemExit(1)
    localstore.restore_database(home_from_env(), Path(rest[0]), replace="--yes" in rest)


def _update(_rest: list[str]) -> None:
    from ._version import __version__

    home = home_from_env()
    problems = localstore.doctor(home)
    print(json.dumps({"version": __version__, "schema_compatible": not any("schema_version" in item for item in problems)}))


def _demo(_rest: list[str]) -> None:
    print(localstore.render_dashboard(home_from_env()))


def _ci(_rest: list[str]) -> None:
    print(
        regression_comment(
            31_000,
            48_000,
            310_000_000,
            "Increased input context length",
        )
    )


def _budget(_rest: list[str]) -> None:
    budget = recommended_budget_micro(49_000_000, 70)
    print(json.dumps({"budget_micro": budget, "warning_micro": warning_micro(budget), "enforce": False}))


def _pid_path() -> Path:
    return home_from_env() / "server.pid"


def _start(_rest: list[str]) -> None:
    import os

    from .localhttp import make_server

    home = home_from_env()
    problems = localstore.doctor(home)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    port = int(os.environ.get("AGENTCOGS_PORT", "3000"))
    server = make_server(home, port)
    _pid_path().write_text(str(os.getpid()), encoding="utf-8")
    print(f"Dashboard: http://127.0.0.1:{server.server_address[1]}")
    try:
        server.serve_forever()
    finally:
        pid = _pid_path()
        if pid.exists():
            pid.unlink()


def _stop(_rest: list[str]) -> None:
    import os
    import signal

    pid_file = _pid_path()
    if not pid_file.exists():
        print("not running")
        return
    pid = int(pid_file.read_text(encoding="utf-8"))
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    if pid_file.exists():
        pid_file.unlink()
    print("stopped")
