import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram_dialog import BgManagerFactory
from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka
from taskiq_redis import RedisStreamBroker

from src.application.mediator import Mediator
from src.infrastructure.broker.taskiq import register_taskiq_tasks
from src.infrastructure.seeds.runner import run_seeds
from src.utils.logging import setup_logging
from src.core.dependencies.providers import make_base_providers
from src.presentation.telegram.middlewares.setup import setup_middlewares


# logging.getLogger("aiogram_dialog").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Старт"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def create_app():
    setup_logging()

    container = make_async_container(
        *make_base_providers(),
        AiogramProvider(),
    )

    async with container() as request_container:
        mediator = await request_container.get(Mediator)
        await run_seeds(mediator)

    broker: RedisStreamBroker = await container.get(RedisStreamBroker)

    register_taskiq_tasks(broker, container=container)
    await broker.startup()

    bot: Bot = await container.get(Bot)
    dp: Dispatcher = await container.get(Dispatcher)

    await set_commands(bot)

    setup_dishka(container=container, router=dp)
    setup_middlewares(dp=dp, container=container)

    await container.get(BgManagerFactory)
    
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        logger.info("🤖 Бот запущен…")
        await dp.start_polling(bot)
    finally:
        await broker.shutdown()
        await bot.session.close()
        logger.info("🧹 Бот остановлены.")


if __name__ == "__main__":
    logger.info("Starting bot")
    asyncio.run(create_app())
