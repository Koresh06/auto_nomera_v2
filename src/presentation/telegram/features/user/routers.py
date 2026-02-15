from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import DialogManager, StartMode

from src.presentation.telegram.features.user.dialogs.create_ad.states import CreateAdSG


router = Router()


@router.message(CommandStart())
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.start(
        CreateAdSG.plate,
        mode=StartMode.RESET_STACK,
    )
