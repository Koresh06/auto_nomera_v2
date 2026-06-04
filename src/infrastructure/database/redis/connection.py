from functools import lru_cache
from redis.asyncio import Redis

from src.core.config import settings


@lru_cache()
def get_redis_client() -> Redis:
    return Redis.from_url(settings.db.redis.url)
