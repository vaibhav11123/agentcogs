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
    the result. If ``gh`` is missing or logged out, prints a clear message
    asking the user to star the repo. A failed star request prints what 
    happened and returns non-zero; ``init()`` ignores that and continues setup.
    """
    gh = shutil.which("gh")
    if not gh:
        _print_star_request()
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
        _print_star_request()
        return 0

    if auth.returncode != 0:
        _print_star_request()
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
        print(f"⭐ Starred {REPO_URL}")
        return 0

    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        print(detail)
    print(f"Could not star {REPO_URL}")
    _print_star_request()
    return result.returncode or 1


def _print_star_request() -> None:
    """Print a visible message asking users to star the repo."""
    print("\n" + "=" * 70)
    print("⭐ If AgentCOGS helps you, please star us on GitHub!")
    print(f"   {REPO_URL}")
    print("=" * 70 + "\n")
