from dishka import Provider, provide, Scope
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram_dialog import BgManagerFactory, setup_dialogs

from src.core.config import settings
from src.application.ports.dialog.teleport import DialogTeleporter
from src.infrastructure.telegram.dialog_teleporter import AiogramDialogTeleporter
from src.presentation.telegram.common.custom_message_manager import CustomMessageManager
from src.presentation.telegram.features import get_all_dialogs, get_all_routers


class TelegramProvider(Provider):
    scope = Scope.APP

    @provide
    def bot(self) -> Bot:
        return Bot(
            token=settings.telegram.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    @provide
    def dispatcher(self, bot: Bot) -> Dispatcher:
        dp = Dispatcher(bot=bot)
        dp.include_routers(*get_all_routers())
        dp.include_routers(*get_all_dialogs())
        dp.workflow_data.pop("bot", None)
        return dp

    @provide
    def bg_manager_factory(self, dp: Dispatcher) -> BgManagerFactory:
        return setup_dialogs(dp, message_manager=CustomMessageManager())
    
    @provide
    def dialog_teleporter(
        self,
        bot: Bot,
        bg_manager_factory: BgManagerFactory,
    ) -> DialogTeleporter:
        return AiogramDialogTeleporter(bot=bot, bg_manager_factory=bg_manager_factory)