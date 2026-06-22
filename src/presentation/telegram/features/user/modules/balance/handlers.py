import logging
from decimal import Decimal, InvalidOperation
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput

from src.domain.enums.payment import PaymentPurpose
from src.presentation.telegram.features.user.modules.payment.helpers import (
    PaymentStartParams,
    start_payment,
)
from src.presentation.telegram.features.user.modules.payment.states import PaymentSG


logger = logging.getLogger(__name__)


async def on_amount_input_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
) -> None:
    try:
        amount = Decimal(value.strip())
        if amount <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("⚠️ Введите корректную сумму, например 500")
        return

    await start_payment(
        dialog_manager,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        params=PaymentStartParams(
            purpose=PaymentPurpose.BALANCE_TOPUP,
            amount=amount,
            description=f"Пополнение баланса на {amount} руб.",
        ),
    )
