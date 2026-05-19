"""CLI: python -m agentcogs outbox status"""
import json
import sys

from .outbox import get_status


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "outbox" and sys.argv[2] == "status":
        print(json.dumps(get_status(), indent=2))
        return
    print("Usage: python -m agentcogs outbox status", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
