from aiogram import Bot
from aiogram_dialog import BgManagerFactory

from src.application.ports.dialog.teleport import DialogTeleporter
from src.presentation.telegram.features.state_registry import resolve_state


class AiogramDialogTeleporter(DialogTeleporter):
    def __init__(
        self,
        bot: Bot,
        bg_manager_factory: BgManagerFactory,
    ) -> None:
        self.bot = bot
        self.bg_manager = bg_manager_factory

    async def switch_to(
        self,
        *,
        user_id: int,
        chat_id: int,
        state_key: str,
        data: dict | None = None,
    ) -> None:
        state = resolve_state(state_key)
        bg = self.bg_manager.bg(bot=self.bot, user_id=user_id, chat_id=chat_id)
        await bg.switch_to(state=state)

    async def update(
        self,
        *,
        user_id: int,
        chat_id: int,
        data: dict,
    ) -> None:
        bg = self.bg_manager.bg(bot=self.bot, user_id=user_id, chat_id=chat_id)
        await bg.update(data)

    async def done(
        self,
        *,
        user_id: int,
        chat_id: int,
    ) -> None:
        bg = self.bg_manager.bg(bot=self.bot, user_id=user_id, chat_id=chat_id)
        await bg.done()