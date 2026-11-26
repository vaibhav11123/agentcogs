import math
import time

import asyncpg
from .config import settings

_QUERY_METHODS = ("execute", "executemany", "fetch", "fetchrow", "fetchval", "fetchmany")


def transaction_pooler(database_url: str) -> bool:
    """Supabase and PgBouncer transaction mode cannot keep a prepared statement."""
    lowered = database_url.lower()
    if "pgbouncer=true" in lowered:
        return True
    return ":6543" in lowered


async def create_pool() -> "ObservedPool":
    """Build asyncpg pool. A transaction-mode pooler forces the statement cache off."""
    cache = 0 if transaction_pooler(settings.database_url) else settings.statement_cache_size
    pool_max = max(1, int(settings.db_pool_max))
    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=min(2, pool_max),
        max_size=pool_max,
        command_timeout=10,
        statement_cache_size=cache,
        max_inactive_connection_lifetime=300,
    )
    return ObservedPool(pool)


def _percentile(samples: list[float], quantile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def _summary(samples: list[float]) -> dict:
    if not samples:
        return {"n": 0, "p50": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "n": len(samples),
        "p50": round(_percentile(samples, 0.50), 3),
        "p99": round(_percentile(samples, 0.99), 3),
        "max": round(max(samples), 3),
    }


class ObservedPool:
    """Times how long a caller waits for a connection, and how long SQL takes."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self.wait_ms: list[float] = []
        self.sql_ms: list[float] = []

    def __getattr__(self, name):
        return getattr(self._pool, name)

    def snapshot(self) -> dict:
        return {
            "pool_wait_ms": _summary(self.wait_ms),
            "sql_ms": _summary(self.sql_ms),
            "pool_size": self._pool.get_size(),
            "pool_idle": self._pool.get_idle_size(),
            "pool_max": self._pool.get_max_size(),
        }

    def acquire(self, *args, **kwargs):
        return _ObservedAcquire(self, self._pool.acquire(*args, **kwargs))

    async def execute(self, *args, **kwargs):
        return await self._query("execute", args, kwargs)

    async def executemany(self, *args, **kwargs):
        return await self._query("executemany", args, kwargs)

    async def fetch(self, *args, **kwargs):
        return await self._query("fetch", args, kwargs)

    async def fetchrow(self, *args, **kwargs):
        return await self._query("fetchrow", args, kwargs)

    async def fetchval(self, *args, **kwargs):
        return await self._query("fetchval", args, kwargs)

    async def _query(self, method: str, args, kwargs):
        started = time.perf_counter()
        async with self._pool.acquire() as conn:
            self.wait_ms.append((time.perf_counter() - started) * 1000)
            query_started = time.perf_counter()
            try:
                return await getattr(conn, method)(*args, **kwargs)
            finally:
                self.sql_ms.append((time.perf_counter() - query_started) * 1000)


class _ObservedAcquire:
    def __init__(self, stats: ObservedPool, manager) -> None:
        self._stats = stats
        self._manager = manager

    async def __aenter__(self):
        started = time.perf_counter()
        conn = await self._manager.__aenter__()
        self._stats.wait_ms.append((time.perf_counter() - started) * 1000)
        return _ObservedConnection(self._stats, conn)

    async def __aexit__(self, exc_type, exc, tb):
        return await self._manager.__aexit__(exc_type, exc, tb)


class _ObservedConnection:
    def __init__(self, stats: ObservedPool, conn) -> None:
        self._stats = stats
        self._conn = conn

    def __getattr__(self, name):
        attr = getattr(self._conn, name)
        if name not in _QUERY_METHODS or not callable(attr):
            return attr
        stats = self._stats

        async def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return await attr(*args, **kwargs)
            finally:
                stats.sql_ms.append((time.perf_counter() - started) * 1000)

        return timed
