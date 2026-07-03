from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.user.manage_admin import (
    ManageAdminCommand,
    AdminAction,
)
from src.domain.entities.user import UserRole
from src.presentation.telegram.features.admin.modules.admin_management.states import (
    AdminManagementSG,
)


async def on_admin_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["target_tg_id"] = int(item_id)
    await dialog_manager.next()


@inject
async def on_revoke_admin(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    tg_id: int = dialog_manager.dialog_data["target_tg_id"]

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    await mediator.handle(
        ManageAdminCommand(user_id=user.id, action=AdminAction.REVOKE)
    )
    await callback.answer("✅ Права администратора сняты")
    await dialog_manager.switch_to(AdminManagementSG.menu)


@inject
async def on_add_tg_id_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        tg_id = int(value.strip())
    except ValueError:
        await message.answer("⚠️ ID должен быть числом")
        return

    try:
        await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    except UserNotFoundException:
        await message.answer(
            "⚠️ Пользователь не найден. Он должен хотя бы раз зайти в бота."
        )
        return

    dialog_manager.dialog_data["target_tg_id"] = tg_id
    await dialog_manager.switch_to(AdminManagementSG.add_confirm)


@inject
async def on_promote_admin(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    tg_id: int = dialog_manager.dialog_data["target_tg_id"]
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    if user.role == UserRole.ADMIN:
        await callback.answer("⚠️ Пользователь уже администратор", show_alert=True)
        return

    await mediator.handle(
        ManageAdminCommand(user_id=user.id, action=AdminAction.PROMOTE)
    )
    await callback.answer("✅ Пользователь назначен администратором")
    await dialog_manager.switch_to(AdminManagementSG.menu)