from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.mediator import Mediator
from src.application.dtos.user import UserDTO
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_user(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id: int = dialog_manager.dialog_data["tg_id"]
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    return {
        "user": user,
        "is_blocked": user.is_blocked,
        "is_payment_blocked": user.is_payment_blocked,
    }
