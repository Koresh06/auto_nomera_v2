import asyncio
from aiogram import Dispatcher
from aiogram_dialog import BgManagerFactory
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka
from taskiq import TaskiqEvents, TaskiqState

from src.core.dependencies.providers import make_base_providers
from src.core.dependencies.providers.taskiq import TaskiqProvider
from src.infrastructure.broker.instance import broker
from src.infrastructure.broker.taskiq import register_taskiq_tasks


container = make_async_container(
    *make_base_providers(),
    TaskiqProvider(),
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def setup_worker(state: TaskiqState) -> None:
    dp: Dispatcher = await container.get(Dispatcher)
    setup_dishka(container=container, router=dp)

    # триггерим создание BgManagerFactory — вызывает setup_dialogs() внутри TelegramProvider
    await container.get(BgManagerFactory)

    register_taskiq_tasks(broker, container=container)


# taskiq worker src.worker:broker