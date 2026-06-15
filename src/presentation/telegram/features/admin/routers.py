import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_dialog import DialogManager, StartMode
from dishka.integrations.aiogram import FromDishka, inject

from src.application.mediator import Mediator
from src.presentation.telegram.features.admin.modules.main.states import MainRegionSG

logger = logging.getLogger(__name__)


router = Router()


@router.message(Command("region"))
@inject
async def create_region_command(
    message: Message,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    await dialog_manager.start(
        MainRegionSG.start,
        mode=StartMode.RESET_STACK,
    )