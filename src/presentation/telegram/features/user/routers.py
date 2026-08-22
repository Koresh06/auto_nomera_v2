import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import DialogManager, StartMode
from dishka.integrations.aiogram import FromDishka, inject

from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.region import RegionStatus
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG


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
        user: UserDTO = await mediator.handle(
            GetTgIdRequest(tg_id=message.from_user.id)
        )
    except UserNotFoundException as ex:
        logger.info(str(ex))
        await dialog_manager.start(
            UserMenuSG.chooise_region,
            mode=StartMode.RESET_STACK,
        )
        return

    region: RegionDTO = await mediator.handle(IdRegionRequest(region_id=user.region_id))

    if region.status != RegionStatus.ACTIVE:
        await message.answer("🚫 <b>Ваш регион был отключён.</b>\nВыберите новый:")
        await dialog_manager.start(
            UserMenuSG.chooise_region,
            mode=StartMode.RESET_STACK,
        )
        return

    await dialog_manager.start(
        UserMenuSG.menu,
        mode=StartMode.RESET_STACK,
    )
