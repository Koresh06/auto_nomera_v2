from dataclasses import dataclass, field
from decimal import Decimal

from aiogram_dialog import DialogManager

from src.domain.enums.payment import PaymentPurpose

from .states import PaymentSG


@dataclass(frozen=True)
class PaymentStartParams:
    purpose: PaymentPurpose
    amount: Decimal
    description: str
    purpose_id: int | None = None
    meta: dict = field(default_factory=dict)
    return_state: str | None = None
    return_data: dict = field(default_factory=dict)


async def start_payment(
    dialog_manager: DialogManager,
    user_id: int,
    chat_id: int,
    params: PaymentStartParams,
) -> None:
    data = {
        "purpose": params.purpose.value,
        "purpose_id": params.purpose_id,
        "amount": str(params.amount),
        "description": params.description,
        "meta": params.meta,
        "return_to": {
            "user_id": user_id,
            "chat_id": chat_id,
        },
    }
    if params.return_state:
        data["return_state"] = params.return_state
        data["return_data"] = params.return_data

    await dialog_manager.start(state=PaymentSG.select_method, data=data)