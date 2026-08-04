from decimal import Decimal
from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput

from src.application.dtos.user import UpdateUserDTO, UserDTO
from src.application.exceptions.user import (
    PaymentBlockedException,
)
from src.application.mediator import Mediator
from src.application.use_cases.payment.create import CreatePaymentRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.user.update import UpdateUserRequest
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose
from src.domain.exceptions.payment import PaymentPhoneRequiredException
from src.presentation.telegram.features.user.modules.payment.states import PaymentSG


@inject
async def on_payment_method_selected(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    method_map = {
        "method_yookassa": PaymentMethod.YOOKASSA,
        "method_stars": PaymentMethod.TELEGRAM_STARS,
    }
    method = method_map.get(widget.widget_id)
    if method is None:
        await callback.answer("❌ Неизвестный способ оплаты.", show_alert=True)
        return

    dialog_manager.dialog_data["payment_method"] = method.value

    await _create_payment_and_route(callback, dialog_manager, mediator, method)


async def _create_payment_and_route(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    mediator: Mediator,
    method: PaymentMethod,
    phone: str | None = None,
) -> None:
    start_data = dialog_manager.start_data
    amount = Decimal(start_data["amount"])
    tg_id = callback.from_user.id

    dialog_manager.dialog_data["amount"] = str(amount)

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))

    meta = {
        **start_data.get("meta", {}),
        "return_to": start_data.get("return_to"),
        "return_state": start_data.get("return_state"),
        "return_data": start_data.get("return_data"),
    }
    if phone:
        meta["phone"] = phone

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
    except PaymentPhoneRequiredException:
        await dialog_manager.switch_to(PaymentSG.waiting_phone)
        return

    if method == PaymentMethod.TELEGRAM_STARS:
        dialog_manager.dialog_data["invoice_link"] = payment.meta.get("invoice_link")
    elif method == PaymentMethod.MANUAL_CARD:
        dialog_manager.dialog_data["card_number"] = payment.meta.get("card")
        dialog_manager.dialog_data["reference"] = payment.meta.get("reference")
    elif method == PaymentMethod.YOOKASSA:
        dialog_manager.dialog_data["confirmation_url"] = payment.meta.get(
            "confirmation_url"
        )

    await dialog_manager.switch_to(PaymentSG.waiting_payment)


@inject
async def on_phone_received_contact(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
):
    value = message.contact.phone_number
    await mediator.handle(
        UpdateUserRequest(
            tg_id=message.from_user.id,
            data=UpdateUserDTO(phone=value),
        )
    )

    await dialog_manager.switch_to(PaymentSG.select_method)


@inject
async def on_phone_input_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
):
    await mediator.handle(
        UpdateUserRequest(
            tg_id=message.from_user.id,
            data=UpdateUserDTO(phone=value),
        )
    )

    await dialog_manager.switch_to(PaymentSG.select_method)
