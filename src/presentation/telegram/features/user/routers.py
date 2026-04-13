import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import DialogManager, StartMode
from dishka.integrations.aiogram import FromDishka, inject

from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.presentation.telegram.features.user.dialogs.start.states import StartSG


logger = logging.getLogger(__name__)


router = Router()


@router.message(CommandStart())
@inject
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        await mediator.handle(GetTgIdRequest(tg_id=message.from_user.id))
        await dialog_manager.start(
            StartSG.menu,
            mode=StartMode.RESET_STACK,
        )
    except UserNotFoundException as ex:
        logger.info(str(ex))
        await dialog_manager.start(
            StartSG.chooise_region,
            mode=StartMode.RESET_STACK,
        )
