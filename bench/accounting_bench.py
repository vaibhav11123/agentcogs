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
                "DB_POOL_MAX": os.environ.get("DB_POOL_MAX", "20"),
                "STATEMENT_CACHE_SIZE": os.environ.get("STATEMENT_CACHE_SIZE", "100"),
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
    event = event_for(row)
    ok, err = emit_event_sync(event)
    retried = False
    if not ok:
        # Same payload, so a replay is the identical bill. The first call already queued it.
        print(json.dumps({"retry": row["run_id"], "error": err}), flush=True)
        ok, err = emit_event_sync(event)
        retried = True
    return {
        "run_id": row["run_id"],
        "customer_id": row["customer_id"],
        "micro": row["micro"],
        "ok": ok,
        "error": err,
        "retried": retried,
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
        "retries": sum(1 for row in rows if row.get("retried")),
        "failure_sample": failures[:8],
        "throughput_rps": (len(rows) / elapsed) if elapsed else 0,
        "latency_ms": {
            "p50": statistics.median(latencies) if latencies else 0,
            "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies or [0]),
            "mean": statistics.fmean(latencies) if latencies else 0,
        },
    }


def concurrent_posts(seconds: float, workers: int, make_row) -> dict:
    """Keep `workers` deliveries in flight until the clock runs out."""
    import threading

    stop_at = time.perf_counter() + seconds
    rows: list[dict] = []
    lock = threading.Lock()

    def run() -> None:
        local = []
        while time.perf_counter() < stop_at:
            local.append(post_delivery(make_row()))
        with lock:
            rows.extend(local)

    started = time.perf_counter()
    threads = [threading.Thread(target=run, daemon=True) for _ in range(max(1, workers))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started
    latencies = [row["ms"] for row in rows]
    failures = [row for row in rows if not row["ok"]]
    return {
        "elapsed_s": round(elapsed, 3),
        "requests": len(rows),
        "failures": len(failures),
        "retries": sum(1 for row in rows if row.get("retried")),
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
                         ledger_facts, cost_events RESTART IDENTITY CASCADE
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
        summary["environment"] = environment(stack)
        from agentcogs.client import reset_client

        for seed in SEEDS:
            for workers in CONCURRENCIES:
                stack.stop_api()
                stack.restart_redis()
                os.environ["REDIS_URL"] = stack.redis_url
                reset_tables()
                outbox.clear_outbox()
                stack.fault = ""
                stack.reconcile_seconds = 3600
                stack.start_api()
                reset_client()
                connect_sdk(stack)
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


def scale_main() -> None:
    """Larger suite: many customers and workspaces, races, edge cases, a hold, repeated passes."""
    import asyncio
    import hashlib

    import asyncpg
    import httpx
    from app.auth import hash_api_key

    runs = int(os.environ.get("ACCOUNTING_BENCH_RUNS", "100000"))
    customers_n = int(os.environ.get("ACCOUNTING_BENCH_CUSTOMERS", "1000"))
    workspace_n = int(os.environ.get("ACCOUNTING_BENCH_WORKSPACES", "10"))
    passes = int(os.environ.get("ACCOUNTING_BENCH_PASSES", "3"))
    hold_s = float(os.environ.get("ACCOUNTING_BENCH_HOLD_SECONDS", "900"))
    races = int(os.environ.get("ACCOUNTING_BENCH_RACES", "10000"))
    database_url = os.environ["DATABASE_URL"]
    RESULTS.mkdir(parents=True, exist_ok=True)
    stack = Stack(database_url)
    summary: dict = {"passes": [], "failures": []}

    def seed_many() -> list[dict]:
        async def _run() -> list[dict]:
            conn = await asyncpg.connect(database_url)
            made = []
            try:
                for index in range(workspace_n):
                    key = f"acg_live_scale{index:02d}"
                    email = f"scale-{index}@example.com"
                    ws = await conn.fetchval(
                        """
                        INSERT INTO workspaces (name, email, api_key)
                        VALUES ($1, $2, $3) RETURNING id
                        """,
                        f"scale-{index}",
                        email,
                        key,
                    )
                    await conn.execute(
                        """
                        INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
                        VALUES ($1, $2, $3)
                        """,
                        ws,
                        hash_api_key(key),
                        key[-4:],
                    )
                    made.append({"id": str(ws), "key": key, "email": email})
            finally:
                await conn.close()
            return made

        return asyncio.run(_run())

    def post_raw(key: str, payload: dict) -> httpx.Response:
        return httpx.post(
            stack.api_url + "/v1/ingest",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=30,
        )

    try:
        stack.start_redis()
        os.environ["REDIS_URL"] = stack.redis_url
        workspaces = seed_many()
        summary["environment"] = environment(stack)
        from agentcogs.client import reset_client

        for pass_index in range(passes):
            stack.stop_api()
            stack.restart_redis()
            os.environ["REDIS_URL"] = stack.redis_url
            reset_tables()
            outbox.clear_outbox()
            stack.fault = ""
            stack.reconcile_seconds = 3600
            stack.start_api()
            reset_client()
            record: dict = {"pass": pass_index, "problems": []}
            per_ws = max(1, runs // workspace_n)
            expected = 0
            posted = 0
            for ws_index, workspace in enumerate(workspaces):
                sdk_init(
                    api_key=workspace["key"],
                    workspace_id=workspace["id"],
                    endpoint=stack.api_url,
                    register_atexit=False,
                    timeout_seconds=30,
                    max_ingest_workers=50,
                )
                from agentcogs.client import reset_client

                reset_client()
                owners = []
                replays = []
                for index in range(per_ws):
                    customer = f"cust-{(ws_index * per_ws + index) % customers_n}"
                    tokens, micro = lanes_for(index)
                    row = {
                        "run_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"scale:{pass_index}:{ws_index}:{index}")),
                        "customer_id": customer,
                        "tokens": tokens,
                        "micro": micro,
                    }
                    owners.append(row)
                    expected += micro
                    if index % 10 < 3:
                        replays.append(dict(row))
                drive([owners, replays], 50, None)
                posted += len(owners)
            async def totals() -> tuple[int, int]:
                conn = await asyncpg.connect(database_url)
                try:
                    micro = await conn.fetchval("SELECT COALESCE(SUM(incurred_micro), 0) FROM ledger_facts")
                    count = await conn.fetchval("SELECT COUNT(*) FROM cost_events")
                finally:
                    await conn.close()
                return int(micro), int(count)

            got_micro, got_count = asyncio.run(totals())
            if got_micro != expected or got_count != posted:
                record["problems"].append(f"money {got_micro} events {got_count} want {expected} {posted}")
            race_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"scale-race:{pass_index}"))
            tokens, micro = lanes_for(0)
            same = event_for({"run_id": race_id, "customer_id": "cust-0", "tokens": tokens, "micro": micro})
            key = workspaces[0]["key"]

            def race_same() -> int:
                response = post_raw(key, same)
                return response.status_code

            with ThreadPoolExecutor(max_workers=50) as pool:
                codes = list(pool.map(lambda _: race_same(), range(races)))
            if any(code != 202 for code in codes):
                record["problems"].append(f"race statuses {sorted(set(codes))}")
            before_race = got_micro
            stored_micro, stored_count = asyncio.run(totals())
            if stored_micro != before_race + micro or stored_count != got_count + 1:
                record["problems"].append(f"race stored {stored_micro}/{stored_count} != {before_race + micro}/{got_count + 1}")
            conflict = dict(same)
            conflict["total_usd"] = micro_as_usd(micro + 5000)
            with ThreadPoolExecutor(max_workers=50) as pool:
                conflict_codes = list(pool.map(lambda _: post_raw(key, conflict).status_code, range(min(races, 100))))
            if any(code != 409 for code in conflict_codes):
                record["problems"].append(f"conflict statuses {sorted(set(conflict_codes))}")
            after_micro, after_count = asyncio.run(totals())
            if after_micro != stored_micro or after_count != stored_count:
                record["problems"].append(f"conflict moved money {after_micro}/{after_count} != {stored_micro}/{stored_count}")
            edges = _edge_cases(workspaces[0]["key"], post_raw)
            record["edges"] = edges
            if any(not item["ok"] for item in edges):
                record["problems"].append("edge case failed")
            sdk_init(
                api_key=workspaces[0]["key"],
                workspace_id=workspaces[0]["id"],
                endpoint=stack.api_url,
                register_atexit=False,
                timeout_seconds=30,
                max_ingest_workers=50,
            )
            reset_client()

            def hold_row() -> dict:
                return {
                    "run_id": str(uuid.uuid4()),
                    "customer_id": "cust-0",
                    "tokens": 100,
                    "micro": expected_micro(100),
                }

            held = concurrent_posts(hold_s, 50, hold_row)
            record["hold_posts"] = held["requests"]
            record["hold_failures"] = held["failures"]
            record["hold_retries"] = held.get("retries", 0)
            record["hold_s"] = held["elapsed_s"]
            record["hold_rps"] = round(held["throughput_rps"], 1)
            record["hold_p99_ms"] = round(held["latency_ms"]["p99"], 1)
            if held["failures"]:
                record["problems"].append(f"hold failures {held['failures']}")
            summary["passes"].append(record)
            if record["problems"]:
                summary["failures"].append(record)
            print(json.dumps({"scale_pass": pass_index, "problems": record["problems"], "hold_posts": held["requests"], "hold_rps": record["hold_rps"], "hold_retries": record["hold_retries"]}), flush=True)
        summary["ok"] = not summary["failures"]
        text = json.dumps(summary, indent=2, sort_keys=True)
        digest = hashlib.sha256(text.encode()).hexdigest()
        summary["sha256"] = digest
        (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        (RESULTS / "summary.sha256").write_text(digest + "\n", encoding="utf-8")
        print(json.dumps({"ok": summary["ok"], "sha256": digest}))
        if not summary["ok"]:
            raise SystemExit(1)
    finally:
        stack.close()


def _edge_cases(key: str, post_raw) -> list[dict]:
    tokens, micro = lanes_for(1)
    base = event_for({"run_id": str(uuid.uuid4()), "customer_id": "cust-0", "tokens": tokens, "micro": micro})
    cases = []

    def check(name: str, payload: dict, status: int) -> None:
        response = post_raw(key, payload)
        cases.append({"name": name, "ok": response.status_code == status, "status": response.status_code})

    check("priced", base, 202)
    mismatch = dict(base)
    mismatch["run_id"] = str(uuid.uuid4())
    mismatch["total_usd"] = micro_as_usd(micro + 1000)
    check("price_mismatch", mismatch, 422)
    lanes = json.loads(json.dumps(base))
    lanes["run_id"] = str(uuid.uuid4())
    lanes["calls"][0]["lanes"]["uncached_input"] = tokens + 3
    lanes["calls"][0]["provider_input_tokens"] = tokens
    check("lane_mismatch", lanes, 422)
    unknown = json.loads(json.dumps(base))
    unknown["run_id"] = str(uuid.uuid4())
    unknown["calls"][0]["lanes"]["not_a_lane"] = 1
    check("unknown_lane", unknown, 422)
    zero = event_for({"run_id": str(uuid.uuid4()), "customer_id": "cust-0", "tokens": 0, "micro": 0})
    zero["total_usd"] = 0
    check("zero_cost", zero, 202)
    dup = dict(base)
    check("duplicate_same", dup, 202)
    changed = dict(base)
    changed["total_usd"] = micro_as_usd(micro + 1000)
    check("duplicate_conflict", changed, 409)
    return cases


def _proc_sample(pid: int) -> dict:
    clk = os.sysconf("SC_CLK_TCK")
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    rest = raw.rsplit(")", 1)[1].split()
    cpu_s = (int(rest[11]) + int(rest[12])) / clk
    read_bytes = 0
    write_bytes = 0
    try:
        for line in Path(f"/proc/{pid}/io").read_text(encoding="utf-8").splitlines():
            key, value = line.split(": ")
            if key == "read_bytes":
                read_bytes = int(value)
            elif key == "write_bytes":
                write_bytes = int(value)
    except OSError:
        pass
    return {"cpu_s": cpu_s, "read_bytes": read_bytes, "write_bytes": write_bytes}


def _comm_sample(*names: str) -> dict:
    """Sum CPU and bytes for every process whose comm is one of names."""
    wanted = set(names)
    clk = os.sysconf("SC_CLK_TCK")
    cpu = 0
    read_bytes = 0
    write_bytes = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip()
            if comm not in wanted:
                continue
            raw = (entry / "stat").read_text(encoding="utf-8")
            rest = raw.rsplit(")", 1)[1].split()
            cpu += int(rest[11]) + int(rest[12])
            for line in (entry / "io").read_text(encoding="utf-8").splitlines():
                key, value = line.split(": ")
                if key == "read_bytes":
                    read_bytes += int(value)
                elif key == "write_bytes":
                    write_bytes += int(value)
        except OSError:
            continue
    return {"cpu_s": cpu / clk, "read_bytes": read_bytes, "write_bytes": write_bytes}


def _host_cpu() -> dict:
    parts = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
    ticks = [int(item) for item in parts]
    idle = ticks[3]
    iowait = ticks[4] if len(ticks) > 4 else 0
    return {"total": sum(ticks), "idle": idle, "iowait": iowait}


def _load_snapshot(stack: Stack) -> dict:
    import urllib.request

    try:
        with urllib.request.urlopen(stack.api_url + "/health/load", timeout=2) as response:
            return json.loads(response.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


def profile_main() -> None:
    """Three passes of one seed. Fresh Postgres rows, Redis, and outbox. Pool stays 20."""
    import threading

    passes = int(os.environ.get("ACCOUNTING_BENCH_PASSES", "3"))
    workers = int(os.environ.get("ACCOUNTING_BENCH_PROFILE_CONCURRENCY", "50"))
    seed = int(os.environ.get("ACCOUNTING_BENCH_PROFILE_SEED", "1"))
    os.environ["DB_POOL_MAX"] = "20"
    database_url = os.environ["DATABASE_URL"]
    out_dir = ROOT / "docs" / "internal"
    out_dir.mkdir(parents=True, exist_ok=True)
    stack = Stack(database_url)
    summary: dict = {
        "seed": seed,
        "passes_requested": passes,
        "concurrency": workers,
        "runs": RUNS,
        "pool_max": 20,
        "passes": [],
    }
    try:
        stack.start_redis()
        os.environ["REDIS_URL"] = stack.redis_url
        seed_workspace()
        summary["environment"] = environment(stack)
        summary["environment"]["cpu_count"] = os.cpu_count()
        summary["environment"]["loadavg"] = Path("/proc/loadavg").read_text(encoding="utf-8").strip()
        from agentcogs.client import reset_client

        for pass_index in range(passes):
            stack.stop_api()
            stack.restart_redis()
            os.environ["REDIS_URL"] = stack.redis_url
            reset_tables()
            outbox.clear_outbox()
            stack.fault = ""
            stack.reconcile_seconds = 3600
            stack.start_api()
            reset_client()
            connect_sdk(stack)
            owners, replays, expected = build_plan(seed, RUNS)
            peak = {"queued": 0}
            stop = {"stop": False}

            def watch(box=peak, flag=stop) -> None:
                while not flag["stop"]:
                    try:
                        queued = int(outbox.backlog()["queued"])
                    except Exception:
                        queued = 0
                    if queued > box["queued"]:
                        box["queued"] = queued
                    time.sleep(0.05)

            watcher = threading.Thread(target=watch, daemon=True)
            watcher.start()
            before = _proc_sample(stack.api.pid)
            before_pg = _comm_sample("postgres")
            before_redis = _comm_sample("redis-server")
            before_host = _host_cpu()
            measured = drive([owners, replays], workers, None)
            after = _proc_sample(stack.api.pid)
            after_pg = _comm_sample("postgres")
            after_redis = _comm_sample("redis-server")
            after_host = _host_cpu()
            stop["stop"] = True
            watcher.join(timeout=2)
            ok, detail = matches(accounting(), expected, RUNS)
            elapsed = max(measured["elapsed_s"], 0.001)
            host_ticks = max(after_host["total"] - before_host["total"], 1)
            record = {
                "pass": pass_index,
                "ok": ok,
                "problems": detail["problems"],
                "requests": measured["requests"],
                "failures": measured["failures"],
                "throughput_rps": round(measured["throughput_rps"], 1),
                "latency_ms": measured["latency_ms"],
                "pool": _load_snapshot(stack),
                "outbox_peak_queued": peak["queued"],
                "api_cpu_s": round(after["cpu_s"] - before["cpu_s"], 3),
                "api_cpu_pct": round(100 * (after["cpu_s"] - before["cpu_s"]) / elapsed, 1),
                "api_read_bytes": after["read_bytes"] - before["read_bytes"],
                "api_write_bytes": after["write_bytes"] - before["write_bytes"],
                "postgres_cpu_s": round(after_pg["cpu_s"] - before_pg["cpu_s"], 3),
                "postgres_read_bytes": after_pg["read_bytes"] - before_pg["read_bytes"],
                "postgres_write_bytes": after_pg["write_bytes"] - before_pg["write_bytes"],
                "redis_cpu_s": round(after_redis["cpu_s"] - before_redis["cpu_s"], 3),
                "host_iowait_pct": round(100 * (after_host["iowait"] - before_host["iowait"]) / host_ticks, 2),
                "host_idle_pct": round(100 * (after_host["idle"] - before_host["idle"]) / host_ticks, 2),
            }
            summary["passes"].append(record)
            print(json.dumps({"profile_pass": pass_index, "ok": ok, "rps": record["throughput_rps"], "p99": record["latency_ms"]["p99"], "pool_wait_p99": record["pool"]["pool_wait_ms"]["p99"] if "pool_wait_ms" in record["pool"] else None, "sql_p99": record["pool"]["sql_ms"]["p99"] if "sql_ms" in record["pool"] else None, "outbox_peak": peak["queued"]}), flush=True)
        summary["ok"] = all(item["ok"] for item in summary["passes"])
        text = json.dumps(summary, indent=2, sort_keys=True)
        (out_dir / "profile-pool20.json").write_text(text, encoding="utf-8")
        print(json.dumps({"wrote": str(out_dir / "profile-pool20.json"), "ok": summary["ok"]}))
        if not summary["ok"]:
            raise SystemExit(1)
    finally:
        stack.close()


if __name__ == "__main__":
    if os.environ.get("ACCOUNTING_BENCH_PROFILE") == "1":
        profile_main()
    elif os.environ.get("ACCOUNTING_BENCH_SCALE") == "1":
        scale_main()
    else:
        main()
