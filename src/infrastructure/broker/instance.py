from src.core.config import settings
from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend


result_backend = RedisAsyncResultBackend(redis_url=settings.db.redis.taskiq_url)
broker = RedisStreamBroker(url=settings.db.redis.taskiq_url).with_result_backend(
    result_backend
)
