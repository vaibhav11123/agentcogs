"""Real-time event emitter for live demos."""
from __future__ import annotations

import argparse
import asyncio
import random
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from generate_events import generate_run  # noqa: E402
from personas import ALL_PERSONAS, PERSONAS  # noqa: E402


class LiveDriftEmitter:
    def __init__(self, endpoint: str, api_key: str, workspace_id: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.client = httpx.AsyncClient(
            base_url=self.endpoint,
            timeout=5,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self.running = True
        self.events_sent = 0
        self.anomalies_sent = 0

    async def emit(self, event: dict) -> bool:
        event["workspace_id"] = self.workspace_id
        event["ts"] = int(time.time())
        try:
            r = await self.client.post("/v1/ingest", json=event)
            return r.status_code == 202
        except Exception as e:
            print(f"⚠️  emit failed: {e}", file=sys.stderr)
            return False

    async def run_background(self, rate_per_min: int = 30) -> None:
        delay = 60.0 / rate_per_min
        print(f"📡 Background drift started ({rate_per_min} events/min)", file=sys.stderr)
        while self.running:
            weights = [p.runs_per_day_mean for p in ALL_PERSONAS]
            persona = random.choices(ALL_PERSONAS, weights=weights, k=1)[0]
            event = generate_run(persona, datetime.now(timezone.utc), is_anomaly=False)
            if await self.emit(event):
                self.events_sent += 1
                if self.events_sent % 10 == 0:
                    print(f"  ✓ {self.events_sent} events sent", file=sys.stderr)
            jitter = delay * random.uniform(0.7, 1.3)
            await asyncio.sleep(jitter)

    async def inject_anomaly(self, persona_id: str | None = None) -> None:
        if persona_id:
            persona = next((p for p in ALL_PERSONAS if p.external_id == persona_id), None)
            if not persona:
                print(f"⚠️  unknown persona: {persona_id}", file=sys.stderr)
                return
        else:
            persona = next(p for p in ALL_PERSONAS if p.external_id == "initech")

        event = generate_run(persona, datetime.now(timezone.utc), is_anomaly=True)
        if await self.emit(event):
            self.anomalies_sent += 1
            mult = event["total_usd"] / max(persona.cost_per_run_mean, 0.0001)
            print(
                f"🔥 ANOMALY injected: {persona.display_name} "
                f"ran '{event['workflow_id']}' for ${event['total_usd']:.4f}",
                file=sys.stderr,
            )
            print(
                f"   ({mult:.1f}× normal ~${persona.cost_per_run_mean:.4f})",
                file=sys.stderr,
            )
            print("   → Watch the dashboard / Alerts page.", file=sys.stderr)

    async def inject_burst(self, persona_id: str = "globex_industries", count: int = 20) -> None:
        persona = next(p for p in ALL_PERSONAS if p.external_id == persona_id)
        print(f"💥 Burst: {count} events from {persona.display_name}", file=sys.stderr)
        for _ in range(count):
            event = generate_run(persona, datetime.now(timezone.utc))
            await self.emit(event)
            await asyncio.sleep(0.1)
        print("   ✓ Burst complete", file=sys.stderr)

    async def interactive_loop(self) -> None:
        import select
        import termios
        import tty

        print(file=sys.stderr)
        print("🎬 Interactive demo controller", file=sys.stderr)
        print("─" * 40, file=sys.stderr)
        print("  a  →  inject anomaly (Initech retry loop)", file=sys.stderr)
        print("  s  →  burst from whale (Globex Industries)", file=sys.stderr)
        print("  m  →  burst from TechFlow (unprofitable customer)", file=sys.stderr)
        print("  i  →  show stats", file=sys.stderr)
        print("  q  →  quit", file=sys.stderr)
        print("─" * 40, file=sys.stderr)
        print(file=sys.stderr)

        def getch() -> str | None:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    return sys.stdin.read(1)
                return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        loop = asyncio.get_event_loop()
        while self.running:
            ch = await loop.run_in_executor(None, getch)
            if ch == "q":
                self.running = False
                break
            if ch == "a":
                await self.inject_anomaly("initech")
            elif ch == "s":
                await self.inject_burst("globex_industries", count=15)
            elif ch == "m":
                await self.inject_burst("techflow_inc", count=10)
            elif ch == "i":
                print(
                    f"📊 Sent: {self.events_sent} normal, "
                    f"{self.anomalies_sent} anomalies",
                    file=sys.stderr,
                )
            await asyncio.sleep(0.05)

    async def close(self) -> None:
        await self.client.aclose()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://localhost:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--rate", type=int, default=30, help="Background events/minute")
    ap.add_argument("--interactive", action="store_true", help="Enable hotkey controls")
    ap.add_argument("--inject-anomaly", action="store_true", help="Fire one anomaly and exit")
    ap.add_argument("--persona", default=None, help="Persona for anomaly (default: initech)")
    args = ap.parse_args()

    emitter = LiveDriftEmitter(args.endpoint, args.api_key, args.workspace_id)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: setattr(emitter, "running", False))

    if args.inject_anomaly:
        await emitter.inject_anomaly(args.persona)
        await emitter.close()
        return

    drift_task = asyncio.create_task(emitter.run_background(args.rate))

    if args.interactive:
        await emitter.interactive_loop()
        drift_task.cancel()
        try:
            await drift_task
        except asyncio.CancelledError:
            pass
    else:
        try:
            await drift_task
        except asyncio.CancelledError:
            pass

    print(
        f"\n📊 Final: {emitter.events_sent} events, {emitter.anomalies_sent} anomalies",
        file=sys.stderr,
    )
    await emitter.close()


if __name__ == "__main__":
    asyncio.run(main())
