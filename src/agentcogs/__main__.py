"""CLI: python -m agentcogs outbox status"""
import json
import sys

from .outbox import get_status
from .usage import capture_usage


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "outbox" and sys.argv[2] == "status":
        try:
            rendered = json.dumps(get_status(), indent=2)
        except Exception:
            capture_usage(command="outbox status", success=False)
            raise
        print(rendered)
        capture_usage(command="outbox status", success=True)
        return
    capture_usage(command="unrecognized", success=False)
    print("Usage: python -m agentcogs outbox status", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
