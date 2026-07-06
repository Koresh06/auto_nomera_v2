import orjson
from dishka import Provider, provide, Scope
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram_dialog import BgManagerFactory, setup_dialogs
from redis.asyncio.client import Redis

from src.core.config import settings
from src.application.ports.dialog.teleport import DialogTeleporter
from src.infrastructure.telegram.dialog_teleporter import AiogramDialogTeleporter
from src.presentation.telegram.common.custom_message_manager import CustomMessageManager
from src.presentation.telegram.features import get_all_dialogs, get_all_routers


class TelegramProvider(Provider):
    scope = Scope.APP

    @provide
    def custom_message_manager(self) -> CustomMessageManager:
        return CustomMessageManager()

    @provide
    def bot(self) -> Bot:
        proxy = settings.telegram.bot_proxy
        session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
        return Bot(
            token=settings.telegram.bot_token,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    @provide
    def fsm_storage(self, redis: Redis) -> RedisStorage:
        return RedisStorage(
            redis=redis,
            key_builder=DefaultKeyBuilder(with_destiny=True),
            json_loads=orjson.loads,
        )

    @provide
    def dispatcher(self, bot: Bot, fsm_storage: RedisStorage) -> Dispatcher:
        dp = Dispatcher(bot=bot, storage=fsm_storage)

        dp.include_routers(*get_all_routers())
        dp.include_routers(*get_all_dialogs())

        dp.workflow_data.pop("bot", None)

        return dp

    @provide
    def bg_manager_factory(self, dp: Dispatcher) -> BgManagerFactory:
        return setup_dialogs(dp)

    @provide
    def dialog_teleporter(
        self,
        bot: Bot,
        bg_manager_factory: BgManagerFactory,
    ) -> DialogTeleporter:
        return AiogramDialogTeleporter(bot=bot, bg_manager=bg_manager_factory)
