#!/usr/bin/env python3
"""Apply SQL migrations in migrations/versions/ (idempotent)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "versions"


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        sys.exit(1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


async def main() -> None:
    conn = await asyncpg.connect(_database_url(), statement_cache_size=0)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            name = path.name
            if await conn.fetchval(
                "SELECT 1 FROM schema_migrations WHERE filename = $1", name
            ):
                print(f"skip {name}")
                continue
            print(f"apply {name}")
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)", name
                )
        print("migrations ok")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
