import logging
from decimal import Decimal
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput

from src.domain.enums.payment import PaymentPurpose
from src.presentation.telegram.utils.price_validators import parse_money
from src.presentation.telegram.features.user.modules.payment.helpers import (
    PaymentStartParams,
    start_payment,
)


logger = logging.getLogger(__name__)


MIN_TOPUP_AMOUNT = Decimal("100")


async def on_amount_input_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
) -> None:
    try:
        amount = parse_money(value)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    if amount <= 0:
        await message.answer("⚠️ Введите корректную сумму, например 500")
        return

    if amount < MIN_TOPUP_AMOUNT:
        await message.answer(
            f"⚠️ Минимальная сумма пополнения — {MIN_TOPUP_AMOUNT:.0f} руб. Попробуйте ещё раз."
        )
        return

    await start_payment(
        dialog_manager,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        params=PaymentStartParams(
            purpose=PaymentPurpose.BALANCE_TOPUP,
            amount=amount,
            description="Пополнение баланса",
            return_state="UserMenuSG:menu",
            return_data={},
        ),
    )
