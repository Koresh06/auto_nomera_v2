from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.user.set_block import (
    SetUserBlockCommand,
    BlockAction,
)
from src.presentation.telegram.features.admin.modules.blocking.states import UserBlockSG


@inject
async def on_user_id_entered(
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
        user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    except UserNotFoundException:
        await message.answer("⚠️ Пользователь не найден")
        return

    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["tg_id"] = user.tg_id
    await dialog_manager.switch_to(UserBlockSG.action)


_ACTION_BY_BUTTON = {
    "block_user": (BlockAction.BLOCK_USER, "🚫 Пользователь заблокирован"),
    "unblock_user": (BlockAction.UNBLOCK_USER, "✅ Пользователь разблокирован"),
    "block_pay": (BlockAction.BLOCK_PAYMENTS, "🚫 Платежи заблокированы"),
    "unblock_pay": (BlockAction.UNBLOCK_PAYMENTS, "✅ Платежи разблокированы"),
}


@inject
async def on_block_action(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    action, toast = _ACTION_BY_BUTTON[button.widget_id]
    user_id: int = dialog_manager.dialog_data["user_id"]

    await mediator.handle(SetUserBlockCommand(user_id=user_id, action=action))
    await callback.answer(toast)
    await dialog_manager.show(show_mode=ShowMode.EDIT)
