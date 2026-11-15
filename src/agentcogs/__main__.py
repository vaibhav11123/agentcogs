"""CLI: python -m agentcogs outbox status | python -m agentcogs star"""
import json
import shutil
import subprocess
import sys

from .outbox import get_status

REPO_URL = "https://github.com/vaibhav11123/agentcogs"
_STAR_API = "/user/starred/vaibhav11123/agentcogs"


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "outbox" and sys.argv[2] == "status":
        print(json.dumps(get_status(), indent=2))
        return
    if sys.argv[1:] == ["star"]:
        code = star()
        if code:
            sys.exit(code)
        return
    print(
        "Usage: python -m agentcogs outbox status\n"
        "       python -m agentcogs star",
        file=sys.stderr,
    )
    sys.exit(1)


def star() -> int:
    """Star the repository when the GitHub CLI is already logged in.

    Runs ``gh auth status``. On a login, runs
    ``gh api --method PUT /user/starred/vaibhav11123/agentcogs`` and prints
    the result. If ``gh`` is missing or logged out, prints the repository URL
    and returns 0 so the rest of the tool is unaffected.
    """
    gh = shutil.which("gh")
    if not gh:
        print(REPO_URL)
        return 0

    try:
        auth = subprocess.run(
            [gh, "auth", "status"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"Could not run gh auth status: {exc}", file=sys.stderr)
        print(REPO_URL)
        return 0

    if auth.returncode != 0:
        print(REPO_URL)
        return 0

    try:
        result = subprocess.run(
            [gh, "api", "--method", "PUT", _STAR_API],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"Could not run gh api: {exc}", file=sys.stderr)
        print(REPO_URL)
        return 1

    if result.returncode == 0:
        for stream in (result.stdout, result.stderr):
            text = (stream or "").strip()
            if text:
                print(text)
        print(f"Starred {REPO_URL}")
        return 0

    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        print(detail, file=sys.stderr)
    print(f"Could not star {REPO_URL}", file=sys.stderr)
    return result.returncode or 1


if __name__ == "__main__":
    main()
