#!/usr/bin/env python3
"""Drive the real SDK against a disposable API, Postgres, and Redis.

The load is 10,000 unique runs, two tenants, and a 20 percent replay.
Concurrency is 1, then 10, then 50. A second phase kills the API after
the database commit and before Redis settlement, restarts Redis, and
replays. One pass keeps writers paused. The next lets writers continue.
Five seeds. No model provider is called.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("GH_CONFIG_DIR", "/tmp/empty-gh")
Path("/tmp/empty-gh").mkdir(parents=True, exist_ok=True)

import agentcogs.outbox as outbox  # noqa: E402

outbox._DB_PATH = Path("/tmp/acg-bench-outbox.db")

from agentcogs.client import emit_event_sync  # noqa: E402
from agentcogs.config import init as sdk_init  # noqa: E402
from agentcogs.localstore import price_book  # noqa: E402
from agentcogs.provider_watch import micro_as_usd  # noqa: E402

RUNS = int(os.environ.get("ACCOUNTING_BENCH_RUNS", "10000"))
SEEDS = [int(item) for item in os.environ.get("ACCOUNTING_BENCH_SEEDS", "1,2,3,4,5").split(",")]
CONCURRENCIES = [int(item) for item in os.environ.get("ACCOUNTING_BENCH_CONCURRENCY", "1,10,50").split(",")]
CRASH_RUNS = int(os.environ.get("ACCOUNTING_BENCH_CRASH_RUNS", "2000"))
API_KEY = "acg_live_accountingbench"
BOOK = price_book()
RESULTS = Path(os.environ.get("ACCOUNTING_BENCH_RESULTS", str(ROOT / "bench" / "results")))
TRACES = RESULTS / "traces"


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for(predicate, seconds: float) -> bool:
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class Stack:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.redis_port = free_port()
        self.api_port = free_port()
        self.redis: subprocess.Popen | None = None
        self.redis_dir: str | None = None
        self.api: subprocess.Popen | None = None
        self.fault = ""
        self.fault_after = 0
        self.reconcile_seconds = 3600

    @property
    def redis_url(self) -> str:
        return f"redis://127.0.0.1:{self.redis_port}/0"

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    def start_redis(self) -> None:
        if self.redis_port == 6379:
            self.redis_port = free_port()
        self.redis_dir = tempfile.mkdtemp(prefix="acg-redis-")
        self.redis = subprocess.Popen(
            [
                "redis-server",
                "--port",
                str(self.redis_port),
                "--bind",
                "127.0.0.1",
                "--save",
                "",
                "--appendonly",
                "no",
                "--protected-mode",
                "yes",
                "--dir",
                self.redis_dir,
                "--dbfilename",
                "dump.rdb",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import redis

        client = redis.Redis.from_url(self.redis_url)

        def ping() -> bool:
            try:
                return bool(client.ping())
            except redis.RedisError:
                return False

        if not wait_for(ping, 10):
            raise RuntimeError("redis did not start")

    def stop_redis(self) -> None:
        if self.redis is not None and self.redis.poll() is None:
            try:
                import redis

                redis.Redis.from_url(self.redis_url).shutdown(nosave=True)
            except Exception:
                self.redis.terminate()
            try:
                self.redis.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.redis.kill()
                self.redis.wait(timeout=5)
        self.redis = None
        if self.redis_dir is not None:
            shutil.rmtree(self.redis_dir, ignore_errors=True)
            self.redis_dir = None

    def restart_redis(self) -> float:
        started = time.perf_counter()
        self.stop_redis()
        self.start_redis()
        import redis

        size = int(redis.Redis.from_url(self.redis_url).dbsize())
        if size != 0:
            raise RuntimeError(f"redis DBSIZE {size} after restart, want 0")
        return time.perf_counter() - started

    def start_api(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": self.database_url,
                "REDIS_URL": self.redis_url,
                "INGEST_RATE_LIMIT": "10000000",
                "RECONCILE_INTERVAL_SECONDS": str(self.reconcile_seconds),
                "ENVIRONMENT": "selfhost",
                "AGENTCOGS_FAULT": self.fault,
                "AGENTCOGS_FAULT_AFTER": str(self.fault_after),
            }
        )
        log_path = RESULTS / "api.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        previous = getattr(self, "_api_log", None)
        if previous is not None and not previous.closed:
            previous.close()
        self._api_log = log_path.open("a", encoding="utf-8")
        self.api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.api_port),
                "--log-level",
                "warning",
            ],
            cwd=str(ROOT / "backend"),
            env=env,
            stdout=self._api_log,
            stderr=subprocess.STDOUT,
        )

        def healthy() -> bool:
            if self.api.poll() is not None:
                return False
            try:
                import urllib.request

                with urllib.request.urlopen(self.api_url + "/health", timeout=0.5) as response:
                    return response.status == 200
            except Exception:
                return False

        if not wait_for(healthy, 20):
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"api did not start\n{tail}")

    def stop_api(self) -> None:
        if self.api is not None and self.api.poll() is None:
            self.api.terminate()
            try:
                self.api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api.kill()
                self.api.wait(timeout=5)
        self.api = None
        log = getattr(self, "_api_log", None)
        if log is not None:
            log.close()
            self._api_log = None

    def close(self) -> None:
        self.stop_api()
        self.stop_redis()


def expected_micro(tokens: int) -> int:
    """Half-up micro-USD from the published fixture rate. Does not call price_call."""
    spec = BOOK["lanes"]["uncached_input"]
    rate = int(BOOK["usd_per_million"][spec["base"]])
    numer = tokens * rate * int(spec["num"])
    den = int(spec["den"])
    quotient, remainder = divmod(numer, den)
    if remainder * 2 >= den:
        quotient += 1
    return quotient


def lanes_for(index: int) -> tuple[int, int]:
    tokens = 100 + (index % 17)
    return tokens, expected_micro(tokens)


def build_plan(seed: int, count: int) -> tuple[list[dict], list[dict], dict[str, int]]:
    rng = random.Random(seed)
    unique = []
    expected = {"tenant_a": 0, "tenant_b": 0}
    for index in range(count):
        tenant = "tenant_a" if rng.randrange(2) == 0 else "tenant_b"
        tokens, micro = lanes_for(index)
        unique.append(
            {
                "run_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"agentcogs-bench:{seed}:{index}")),
                "customer_id": tenant,
                "tokens": tokens,
                "micro": micro,
            }
        )
        expected[tenant] += micro
    replays = []
    for index, row in enumerate(unique):
        if index % 5 != 0:
            continue
        replay = dict(row)
        if index % 10 == 0:
            replay["customer_id"] = "tenant_b" if row["customer_id"] == "tenant_a" else "tenant_a"
            replay["cross_tenant"] = True
        replays.append(replay)
    rng.shuffle(unique)
    rng.shuffle(replays)
    return unique, replays, expected


def event_for(row: dict) -> dict:
    micro = int(row["micro"])
    tokens = int(row["tokens"])
    usd = micro_as_usd(micro)
    return {
        "run_id": row["run_id"],
        "customer_id": row["customer_id"],
        "workflow_id": "bench",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": usd,
        "models": {"gpt-4o-mini": {"input_tokens": tokens, "output_tokens": 0, "usd": usd}},
        "node_costs": {},
        "metadata": {},
        "error": None,
        "book_id": "fixture-v1",
        "calls": [
            {
                "call_id": "c0",
                "model": "gpt-4o-mini",
                "lanes": {
                    "uncached_input": tokens,
                    "cache_read": 0,
                    "cache_write_5m": 0,
                    "cache_write_1h": 0,
                    "cache_write_30m": 0,
                    "cache_write_12h": 0,
                    "output": 0,
                    "reasoning": 0,
                },
                "provider_input_tokens": tokens,
            }
        ],
    }


def naive_charge(waves: list[list[dict]]) -> dict[str, int]:
    """Add every delivery, including a second add for a replay. No idempotency."""
    spent = {"tenant_a": 0, "tenant_b": 0}
    for wave in waves:
        for row in wave:
            spent[row["customer_id"]] += int(row["micro"])
    return spent


def connect_sdk(stack: Stack) -> None:
    sdk_init(
        api_key=API_KEY,
        workspace_id="ws_bench",
        endpoint=stack.api_url,
        register_atexit=False,
        timeout_seconds=30,
        max_ingest_workers=max(CONCURRENCIES),
    )


def post_delivery(row: dict) -> dict:
    started = time.perf_counter()
    ok, err = emit_event_sync(event_for(row))
    return {
        "run_id": row["run_id"],
        "customer_id": row["customer_id"],
        "micro": row["micro"],
        "ok": ok,
        "error": err,
        "ms": (time.perf_counter() - started) * 1000,
    }


def drive(waves: list[list[dict]], workers: int, trace) -> dict:
    """Post each wave to completion before the next. Owners land before replays."""
    started = time.perf_counter()
    rows = []
    for deliveries in waves:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(post_delivery, deliveries):
                rows.append(result)
                if trace is not None:
                    trace.write(json.dumps(result) + "\n")
    elapsed = time.perf_counter() - started
    latencies = [row["ms"] for row in rows]
    failures = [row for row in rows if not row["ok"]]
    return {
        "elapsed_s": elapsed,
        "requests": len(rows),
        "failures": len(failures),
        "failure_sample": failures[:8],
        "throughput_rps": (len(rows) / elapsed) if elapsed else 0,
        "latency_ms": {
            "p50": statistics.median(latencies) if latencies else 0,
            "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies or [0]),
            "mean": statistics.fmean(latencies) if latencies else 0,
        },
    }


def reset_tables() -> None:
    import asyncio

    import asyncpg

    async def _run() -> None:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            await conn.execute(
                """
                TRUNCATE anomalies, allocation_lines, settlement_receipts, ledger_drift,
                         ledger_facts, cost_events, customers RESTART IDENTITY CASCADE
                """
            )
        finally:
            await conn.close()

    asyncio.run(_run())


def seed_workspace() -> None:
    import asyncio

    import asyncpg
    from app.auth import hash_api_key

    async def _run() -> None:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            existing = await conn.fetchval("SELECT id FROM workspaces WHERE email = 'bench@example.com'")
            if existing:
                return
            ws = await conn.fetchval(
                """
                INSERT INTO workspaces (name, email, api_key, plan)
                VALUES ('Bench', 'bench@example.com', $1, 'pro')
                RETURNING id
                """,
                API_KEY,
            )
            await conn.execute(
                """
                INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
                VALUES ($1, $2, $3)
                """,
                ws,
                hash_api_key(API_KEY),
                API_KEY[-4:],
            )
        finally:
            await conn.close()

    asyncio.run(_run())


def accounting() -> dict:
    import asyncio

    import asyncpg
    import redis
    from app.services.admission import spent_micro

    async def _spent(url: str, ws: str, cust: str) -> int:
        client = redis.asyncio.Redis.from_url(url, decode_responses=True)
        try:
            return await spent_micro(client, ws, cust)
        finally:
            await client.aclose()

    async def _run() -> dict:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            rows = await conn.fetch(
                """
                SELECT c.external_id, c.id::text AS id,
                       COALESCE(SUM(f.incurred_micro), 0)::bigint AS micro,
                       COUNT(f.run_id)::bigint AS runs
                FROM customers c
                LEFT JOIN ledger_facts f ON f.customer_id = c.id
                GROUP BY c.external_id, c.id
                """
            )
            facts = await conn.fetchval("SELECT COUNT(*) FROM ledger_facts")
            events = await conn.fetchval("SELECT COUNT(*) FROM cost_events")
            receipts = await conn.fetch(
                """
                SELECT c.external_id, COALESCE(SUM(r.actual_micro), 0)::bigint AS micro
                FROM customers c
                LEFT JOIN settlement_receipts r ON r.customer_id = c.id
                GROUP BY c.external_id
                """
            )
            workspaces = await conn.fetchval("SELECT COUNT(DISTINCT workspace_id) FROM ledger_facts")
            ws = await conn.fetchval("SELECT id::text FROM workspaces WHERE email = 'bench@example.com'")
        finally:
            await conn.close()
        by_tenant = {}
        redis_url = os.environ["REDIS_URL"]
        receipt_by_tenant = {row["external_id"]: int(row["micro"]) for row in receipts}
        for row in rows:
            redis_spent = await _spent(redis_url, ws, row["id"])
            by_tenant[row["external_id"]] = {
                "ledger_micro": int(row["micro"]),
                "runs": int(row["runs"]),
                "redis_micro": int(redis_spent),
                "receipt_micro": receipt_by_tenant.get(row["external_id"], 0),
                "workspace_id": ws,
            }
        return {
            "tenants": by_tenant,
            "facts": int(facts),
            "events": int(events),
            "receipt_micro": sum(receipt_by_tenant.values()),
            "workspaces": int(workspaces or 0),
        }

    return asyncio.run(_run())


def matches(got: dict, expected: dict[str, int], runs: int) -> tuple[bool, dict]:
    problems = []
    if got["facts"] != runs or got["events"] != runs:
        problems.append(f"rows facts={got['facts']} events={got['events']} want={runs}")
    if runs and got.get("workspaces") != 1:
        problems.append(f"workspaces {got.get('workspaces')} != 1")
    if got["receipt_micro"] != sum(expected.values()):
        problems.append(f"receipts {got['receipt_micro']} != {sum(expected.values())}")
    for tenant, micro in expected.items():
        row = got["tenants"].get(tenant)
        if row is None:
            if micro != 0:
                problems.append(f"missing {tenant}")
            continue
        if row["ledger_micro"] != micro:
            problems.append(f"{tenant} ledger {row['ledger_micro']} != {micro}")
        if row["receipt_micro"] != micro:
            problems.append(f"{tenant} receipts {row['receipt_micro']} != {micro}")
        if row["redis_micro"] != micro:
            problems.append(f"{tenant} redis {row['redis_micro']} != {micro}")
    return not problems, {"problems": problems, "got": got}


def wait_until_match(expected: dict[str, int], runs: int, seconds: float, started: float | None = None) -> tuple[float, dict]:
    started = time.perf_counter() if started is None else started
    last = {}
    while time.perf_counter() - started < seconds:
        last = accounting()
        ok, detail = matches(last, expected, runs)
        if ok:
            return time.perf_counter() - started, detail
        time.sleep(0.2)
    ok, detail = matches(last, expected, runs)
    detail["problems"].append("recovery timed out")
    return time.perf_counter() - started, detail


def percentile_chart(summary: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = [cell for cell in summary["cells"] if cell["phase"] == "load"]
    concurrencies = sorted({cell["concurrency"] for cell in cells})
    means = []
    lows = []
    highs = []
    for conc in concurrencies:
        group = [cell["throughput_rps"] for cell in cells if cell["concurrency"] == conc]
        mean = statistics.fmean(group)
        means.append(mean)
        lows.append(mean - min(group))
        highs.append(max(group) - mean)
    ledger = sum(cells[0]["expected_micro"].values()) / 1_000_000
    naive = ledger + (cells[0]["naive_overshoot_micro"] / 1_000_000)
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8))
    axes[0].bar([str(item) for item in concurrencies], means, color="#1f4b99", yerr=[lows, highs], capsize=4, ecolor="#0f172a")
    axes[0].set_title("Throughput across five seeds")
    axes[0].set_xlabel("Concurrent SDK posts")
    axes[0].set_ylabel("Requests / second")
    bars = axes[1].bar(["Ledger", "Naive precheck"], [ledger, naive], color=["#1f4b99", "#9a3412"])
    axes[1].set_title("Dollars charged for one seed")
    axes[1].set_ylabel("USD")
    for bar, value in zip(bars, (ledger, naive)):
        axes[1].text(bar.get_x() + bar.get_width() / 2, value + 0.04, f"${value:.3f}", ha="center", va="bottom", fontsize=9)
    axes[1].set_ylim(0, naive * 1.18)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def environment(stack: Stack) -> dict:
    import asyncpg
    import platform

    async def _pg() -> str:
        conn = await asyncpg.connect(stack.database_url)
        try:
            return await conn.fetchval("SELECT version()")
        finally:
            await conn.close()

    import asyncio

    import redis

    info = redis.Redis.from_url(stack.redis_url).info("server")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "postgres": asyncio.run(_pg()),
        "redis": info.get("redis_version"),
        "runs": RUNS,
        "crash_runs": CRASH_RUNS,
        "seeds": SEEDS,
        "concurrency": CONCURRENCIES,
        "ingest_rate_limit": 10_000_000,
        "commit": os.environ.get("GIT_COMMIT", ""),
    }


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = database_url
    RESULTS.mkdir(parents=True, exist_ok=True)
    TRACES.mkdir(parents=True, exist_ok=True)
    stack = Stack(database_url)
    summary: dict = {"cells": [], "recoveries": [], "failures": []}
    try:
        stack.start_redis()
        os.environ["REDIS_URL"] = stack.redis_url
        seed_workspace()
        stack.reconcile_seconds = 3600
        stack.start_api()
        connect_sdk(stack)
        summary["environment"] = environment(stack)
        for seed in SEEDS:
            for workers in CONCURRENCIES:
                reset_tables()
                outbox.clear_outbox()
                owners, replays, expected = build_plan(seed, RUNS)
                naive = naive_charge([owners, replays])
                trace_path = TRACES / f"load-seed{seed}-c{workers}.jsonl"
                with trace_path.open("w", encoding="utf-8") as trace:
                    measured = drive([owners, replays], workers, trace)
                ok, detail = matches(accounting(), expected, RUNS)
                cell = {
                    "phase": "load",
                    "seed": seed,
                    "concurrency": workers,
                    "ok": ok,
                    "expected_micro": expected,
                    "naive_micro": naive,
                    "naive_overshoot_micro": sum(naive.values()) - sum(expected.values()),
                    **measured,
                    "check": detail,
                }
                summary["cells"].append(cell)
                print(json.dumps({"load": seed, "concurrency": workers, "ok": ok, "rps": round(measured["throughput_rps"], 1)}), flush=True)
                if not ok:
                    summary["failures"].append(cell)
                    print(json.dumps({"failed": cell["check"]["problems"]}), flush=True)
        stack.stop_api()
        import threading

        for seed in SEEDS:
            for mode in ("paused", "continuing"):
                reset_tables()
                outbox.clear_outbox()
                owners, replays, expected = build_plan(seed + 100, CRASH_RUNS)
                stack.fault = "after_commit"
                stack.fault_after = 40
                stack.reconcile_seconds = 3600
                stack.start_api()
                from agentcogs.client import reset_client

                reset_client()
                drive([owners, replays], 10, None)
                died = stack.api is not None and stack.api.poll() is not None
                if not died:
                    summary["failures"].append({"phase": "crash", "seed": seed, "mode": mode, "problems": ["api did not exit"]})
                    stack.stop_api()
                    continue
                redis_restart_s = stack.restart_redis()
                recovery_started = time.perf_counter()
                os.environ["REDIS_URL"] = stack.redis_url
                gap = accounting()
                ledger_now = sum(row["ledger_micro"] for row in gap["tenants"].values())
                redis_now = sum(row["redis_micro"] for row in gap["tenants"].values())
                stack.fault = ""
                stack.reconcile_seconds = 0.5
                stack.start_api()
                reset_client()
                extra = {"tenant_a": 0, "tenant_b": 0, "runs": 0}
                stop_extra = {"stop": False}

                def extra_writer(box=extra, flag=stop_extra, seed_value=seed, mode_name=mode) -> None:
                    index = 0
                    while not flag["stop"]:
                        tenant = "tenant_a" if index % 2 == 0 else "tenant_b"
                        tokens, micro = lanes_for(index)
                        row = {
                            "run_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"agentcogs-bench-extra:{seed_value}:{mode_name}:{index}")),
                            "customer_id": tenant,
                            "tokens": tokens,
                            "micro": micro,
                        }
                        result = post_delivery(row)
                        if result["ok"]:
                            box[tenant] += micro
                            box["runs"] += 1
                        index += 1

                writer = None
                if mode == "continuing":
                    writer = threading.Thread(target=extra_writer, daemon=True)
                    writer.start()
                drive([owners, replays], 10, None)
                if writer is not None:
                    stop_extra["stop"] = True
                    writer.join(timeout=30)
                combined = {tenant: expected[tenant] + extra[tenant] for tenant in expected}
                recovery_s, detail = wait_until_match(combined, CRASH_RUNS + extra["runs"], 90, recovery_started)
                record = {
                    "phase": "recovery",
                    "seed": seed,
                    "mode": mode,
                    "redis_restart_s": redis_restart_s,
                    "redis_gap_before_replay_micro": ledger_now - redis_now,
                    "recovery_s": recovery_s,
                    "ok": not detail["problems"],
                    "check": detail,
                    "extra_micro": {tenant: extra[tenant] for tenant in ("tenant_a", "tenant_b")},
                    "extra_runs": extra["runs"],
                }
                summary["recoveries"].append(record)
                print(json.dumps({"recovery": mode, "seed": seed, "ok": record["ok"], "recovery_s": round(recovery_s, 3)}), flush=True)
                if record["ok"] is False:
                    summary["failures"].append(record)
                stack.stop_api()
        summary["ok"] = not summary["failures"]
        (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        try:
            percentile_chart(summary, RESULTS / "chart.png")
        except Exception as exc:
            print(json.dumps({"chart": str(exc)}), flush=True)
        print(json.dumps({"ok": summary["ok"], "cells": len(summary["cells"]), "recoveries": len(summary["recoveries"]), "failures": len(summary["failures"])}))
        if not summary["ok"]:
            raise SystemExit(1)
    finally:
        stack.close()


if __name__ == "__main__":
    main()
