import asyncpg
from .config import settings


def transaction_pooler(database_url: str) -> bool:
    """Supabase and PgBouncer transaction mode cannot keep a prepared statement."""
    lowered = database_url.lower()
    if "pgbouncer=true" in lowered:
        return True
    return ":6543" in lowered


async def create_pool() -> asyncpg.Pool:
    """Build asyncpg pool. A transaction-mode pooler forces the statement cache off."""
    cache = 0 if transaction_pooler(settings.database_url) else settings.statement_cache_size
    pool_max = max(1, int(settings.db_pool_max))
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=min(2, pool_max),
        max_size=pool_max,
        command_timeout=10,
        statement_cache_size=cache,
        max_inactive_connection_lifetime=300,
    )
