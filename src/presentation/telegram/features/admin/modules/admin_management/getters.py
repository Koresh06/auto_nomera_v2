from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.mediator import Mediator
from src.application.use_cases.user.get_admin import GetAdminsCommand
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.dtos.user import UserDTO
from src.domain.entities.user import UserRole


@inject
async def getter_admins_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    admins: list[UserDTO] = await mediator.handle(GetAdminsCommand())
    return {"admins": admins, "has_admins": bool(admins)}


@inject
async def getter_admin_detail(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id: int = dialog_manager.dialog_data["target_tg_id"]
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    return {
        "user": user,
        "username": user.username or "—",
        "full_name": user.full_name or "—",
        "phone": user.phone or "—",
    }


@inject
async def getter_add_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id: int = dialog_manager.dialog_data["target_tg_id"]
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    is_admin = user.role == UserRole.ADMIN

    return {
        "user": user,
        "username": user.username or "—",
        "is_admin": is_admin,
        "role_label": ("🛡 Администратор" if is_admin else "👤 Пользователь"),
    }
