from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.dtos.user import UserDTO


@inject
async def getter_user_balance(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id: int = dialog_manager.dialog_data["tg_id"]
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    return {
        "user": user,
        "balance": user.balance_display,
    }


async def getter_confirm(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    amount: str = data.get("amount", "")
    is_negative = amount.startswith("-")

    return {
        "tg_id": data.get("tg_id", "—"),
        "username": data.get("username") or "—",
        "current_balance": data.get("current_balance", "—"),
        "amount": amount,
        "operation": "➖ Списать" if is_negative else "➕ Начислить",
        "abs_amount": amount.lstrip("+-"),
    }