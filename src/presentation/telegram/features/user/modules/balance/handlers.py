import logging
from decimal import Decimal, InvalidOperation
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput

from src.domain.enums.payment import PaymentPurpose
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

    await dialog_manager.start(
        state=PaymentSG.select_method,
        data={
            "purpose": PaymentPurpose.BALANCE_TOPUP.value,
            "amount": str(amount),
            "description": f"Пополнение баланса на {amount} руб.",
        },
    )


