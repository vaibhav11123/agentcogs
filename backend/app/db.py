import asyncpg
from .config import settings


async def create_pool() -> asyncpg.Pool:
    """Build asyncpg pool. statement_cache_size=0 is REQUIRED for
    Supabase transaction-mode pooler (port 6543)."""
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=20,
        command_timeout=10,
        statement_cache_size=0,
        max_inactive_connection_lifetime=300,
    )
