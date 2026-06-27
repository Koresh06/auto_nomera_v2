from aiogram import Bot
from aiogram_dialog import BgManagerFactory, ShowMode, StartMode

from src.application.ports.dialog.teleport import DialogTeleporter
from src.presentation.telegram.features.state_registry import resolve_state


class AiogramDialogTeleporter(DialogTeleporter):
    def __init__(self, bot: Bot, bg_manager: BgManagerFactory) -> None:
        self.bot = bot
        self.bg_manager = bg_manager

    async def start(
        self,
        *,
        user_id: int,
        chat_id: int,
        state_key: str,
        data: dict | None = None,
    ) -> None:
        state = resolve_state(state_key)
        bg = self.bg_manager.bg(
            bot=self.bot,
            user_id=user_id,
            chat_id=chat_id,
            load=True,
        )
    
        await bg.start(
            state=state,
            data=data or {},
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
        )