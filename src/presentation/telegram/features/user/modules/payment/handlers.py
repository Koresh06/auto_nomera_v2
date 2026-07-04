from decimal import Decimal
from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick

from src.application.dtos.user import UserDTO
from src.application.exceptions.user import PaymentBlockedException
from src.application.mediator import Mediator
from src.application.use_cases.payment.create import CreatePaymentRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose


@inject
async def on_payment_method_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    start_data = dialog_manager.start_data
    method = PaymentMethod(item_id)
    amount = Decimal(start_data["amount"])
    tg_id = callback.from_user.id

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    meta = {
        **start_data.get("meta", {}),
        "return_to": start_data.get("return_to"),
        "return_state": start_data.get("return_state"),
        "return_data": start_data.get("return_data"),
    }

    try:
        payment: Payment = await mediator.handle(
            CreatePaymentRequest(
                user_id=user.id,
                amount=amount,
                method=method,
                purpose=PaymentPurpose(start_data["purpose"]),
                purpose_id=start_data.get("purpose_id"),
                description=start_data.get("description"),
                meta=meta,
            )
        )
    except PaymentBlockedException:
        await callback.answer(
            "🚫 Платежи для вашего аккаунта заблокированы. Обратитесь в поддержку.",
            show_alert=True,
        )
        return

    dialog_manager.dialog_data["payment_method"] = method.value
    dialog_manager.dialog_data["amount"] = str(amount)

    if method == PaymentMethod.TELEGRAM_STARS:
        dialog_manager.dialog_data["invoice_link"] = payment.meta.get("invoice_link")
    elif method == PaymentMethod.MANUAL_CARD:
        dialog_manager.dialog_data["card_number"] = payment.meta.get("card")
        dialog_manager.dialog_data["reference"] = payment.meta.get("reference")
    elif method == PaymentMethod.YOOKASSA:
        dialog_manager.dialog_data["confirmation_url"] = payment.meta.get(
            "confirmation_url"
        )

    await dialog_manager.next()
