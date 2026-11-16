"""Star the GitHub repository with the person's existing ``gh`` login.

Called from ``agentcogs.init()``. Importing this module does not star anything.
"""
import shutil
import subprocess

REPO_URL = "https://github.com/vaibhav11123/agentcogs"
_STAR_API = "/user/starred/vaibhav11123/agentcogs"


def star() -> int:
    """Star the repository when the GitHub CLI is already logged in.

    Runs ``gh auth status``. On a login, runs
    ``gh api --method PUT /user/starred/vaibhav11123/agentcogs`` and prints
    the result. If ``gh`` is missing or logged out, prints the repository URL
    and returns 0. A failed star request prints what happened and returns
    non-zero; ``init()`` ignores that and continues setup.
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
        print(f"Could not run gh auth status: {exc}")
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
        print(f"Could not run gh api: {exc}")
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
        print(detail)
    print(f"Could not star {REPO_URL}")
    return result.returncode or 1
