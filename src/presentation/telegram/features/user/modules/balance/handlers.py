import logging
from decimal import Decimal, InvalidOperation
from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.payment.create import CreatePaymentRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose


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

    dialog_manager.dialog_data["amount"] = str(amount)
    await dialog_manager.next()


@inject
async def on_method_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    method = PaymentMethod(item_id)
    amount = Decimal(dialog_manager.dialog_data["amount"])
    tg_id = callback.from_user.id

    logger.info(f"[Topup] method={method} amount={amount} tg_id={tg_id}")

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    payment: Payment = await mediator.handle(
        CreatePaymentRequest(
            user_id=user.id,
            amount=amount,
            method=method,
            purpose=PaymentPurpose.BALANCE_TOPUP,
            description=f"Пополнение баланса на {amount} руб.",
        )
    )

    logger.info(f"[Topup:created] external_id={payment.external_id} status={payment.status}")

    dialog_manager.dialog_data["payment_external_id"] = payment.external_id
    dialog_manager.dialog_data["payment_method"] = method.value

    if method == PaymentMethod.TELEGRAM_STARS:
        dialog_manager.dialog_data["invoice_link"] = payment.meta.get("invoice_link")
        logger.info(f"[Topup:stars] invoice_link={payment.meta.get('invoice_link')}")
    elif method == PaymentMethod.MANUAL_CARD:
        dialog_manager.dialog_data["card_number"] = payment.meta.get("card")
        dialog_manager.dialog_data["reference"] = payment.meta.get("reference")
        logger.info(f"[Topup:card] card={payment.meta.get('card')} reference={payment.meta.get('reference')}")

    await dialog_manager.next()