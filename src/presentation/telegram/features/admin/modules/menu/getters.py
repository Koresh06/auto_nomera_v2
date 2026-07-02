from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.core.config import settings
from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.role import UserRole


@inject
async def getter_admin_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id = dialog_manager.event.from_user.id

    if tg_id in settings.telegram.admin_ids:
        return {"is_admin": True, "is_super_admin": True}

    try:
        user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id))
    except UserNotFoundException:
        return {"is_admin": False, "is_super_admin": False}

    return {
        "is_admin": user.role == UserRole.ADMIN,
        "is_super_admin": False,
    }
