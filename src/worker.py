from dishka import make_async_container
from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend

from src.core.config import settings
from src.core.dependencies.providers import make_base_providers
from src.core.dependencies.providers.taskiq import TaskiqProvider
from src.infrastructure.broker.taskiq import register_taskiq_tasks

container = make_async_container(
    *make_base_providers(),
    TaskiqProvider(),
)

result_backend = RedisAsyncResultBackend(redis_url=settings.db.redis.taskiq_url)
broker = RedisStreamBroker(
    url=settings.db.redis.taskiq_url
).with_result_backend(result_backend)

register_taskiq_tasks(broker, container=container)

# taskiq worker src.worker:broker