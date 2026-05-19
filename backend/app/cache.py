from redis.asyncio import Redis
from .config import settings


def create_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)
