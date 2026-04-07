from dishka import Provider, Scope, provide
from aiogram import Bot

from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.infrastructure.telegram.aiogram_publisher import AiogramTelegramPublisher


class TelegramPublisherProvider(Provider):
    scope = Scope.APP

    @provide
    def telegram_publisher(self, bot: Bot) -> TelegramPublisher:
        return AiogramTelegramPublisher(bot)
