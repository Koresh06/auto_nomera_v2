import asyncio

from dishka import make_async_container
from taskiq_redis import RedisStreamBroker

from src.application.mediator import Mediator
from src.core.dependencies.providers import make_base_providers
from src.core.dependencies.providers.taskiq import TaskiqProvider
from src.infrastructure.broker.taskiq import register_taskiq_tasks


async def _build():
    container = make_async_container(
        *make_base_providers(),
        TaskiqProvider(),
    )

    async def get_mediator() -> Mediator:
        async with container() as request_container:
            return await request_container.get(Mediator)

    broker = await container.get(RedisStreamBroker)

    register_taskiq_tasks(broker, get_mediator=get_mediator)

    return broker


broker = asyncio.get_event_loop().run_until_complete(_build())