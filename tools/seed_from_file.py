"""Replay a JSONL file of cost events to a running backend."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx


async def replay(
    path: str,
    *,
    endpoint: str,
    api_key: str,
    workspace_id: str,
    rate: float,
) -> None:
    sent = failed = 0
    delay = 1.0 / rate if rate > 0 else 0
    async with httpx.AsyncClient(
        base_url=endpoint.rstrip("/"),
        timeout=10,
        headers={"Authorization": f"Bearer {api_key}"},
    ) as client:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                ev["workspace_id"] = workspace_id
                try:
                    r = await client.post("/v1/ingest", json=ev)
                    if r.status_code == 202:
                        sent += 1
                    else:
                        failed += 1
                        print(f"⚠️ {r.status_code}: {r.text[:120]}", file=sys.stderr)
                except Exception as e:
                    failed += 1
                    print(f"⚠️ {e}", file=sys.stderr)
                if delay:
                    await asyncio.sleep(delay)
    print(f"✅ replay done: sent={sent} failed={failed}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay events.jsonl to /v1/ingest")
    ap.add_argument("file", help="JSONL path")
    ap.add_argument("--endpoint", default="http://localhost:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--rate", type=float, default=100.0, help="Events per second (0 = max)")
    args = ap.parse_args()
    asyncio.run(
        replay(
            args.file,
            endpoint=args.endpoint,
            api_key=args.api_key,
            workspace_id=args.workspace_id,
            rate=args.rate,
        )
    )


if __name__ == "__main__":
    main()
