from dishka import Provider, provide, Scope
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.core.config import settings


class TgBotProvider(Provider):
    scope = Scope.APP

    @provide
    def bot(self) -> Bot:
        return Bot(
            token=settings.telegram.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    @provide
    def dispatcher(self, bot: Bot) -> Dispatcher:
        return Dispatcher(bot=bot)