from decimal import Decimal

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.domain.exceptions.user import InsufficientBalance
from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceCommand,
)


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
        await message.answer("⚠️ Пользователь с таким ID не найден")
        return

    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["tg_id"] = user.tg_id
    dialog_manager.dialog_data["username"] = user.username
    dialog_manager.dialog_data["current_balance"] = str(user.balance)

    await dialog_manager.next()


async def on_amount_entered(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: Decimal,
) -> None:
    data = dialog_manager.dialog_data
    data["amount"] = f"{'+' if value > 0 else ''}{value:.0f}"
    data["amount_raw"] = str(value)
    await dialog_manager.next()


@inject
async def on_balance_confirm(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    user_id: int = data["user_id"]
    amount = Decimal(data["amount_raw"])

    try:
        await mediator.handle(AdminAdjustBalanceCommand(user_id=user_id, amount=amount))
    except InsufficientBalance:
        await callback.answer(
            "⚠️ Недостаточно средств для списания такой суммы",
            show_alert=True,
        )
        return

    await callback.answer("✅ Баланс изменён")
    await dialog_manager.done()
