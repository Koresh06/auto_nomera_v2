from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Cancel,
    Select,
    Back,
    ScrollingGroup,
    Url,
)

from src.domain.enums.payment import PaymentMethod
from src.presentation.telegram.features.error_handlers import on_input_error

from .states import TopupSG
from .handlers import on_method_selected, on_amount_input_success
from .getters import getter_select_method


topup_dialog = Dialog(
    Window(
        Const("💰 <b>Пополнение баланса</b>\n\nВведите сумму в рублях:"),
        TextInput(
            id="amount_input",
            type_factory=str,
            on_success=on_amount_input_success,
            on_error=on_input_error,
        ),
        Cancel(Const("⬅️ Назад")),
        state=TopupSG.enter_amount,
    ),
    Window(
        Format("💰 Сумма пополнения: <b>{amount} руб.</b>\n\nВыберите способ оплаты:"),
        ScrollingGroup(
            Select(
                Format("{item[title]}"),
                id="method_select",
                items="methods",
                item_id_getter=lambda it: it["id"],
                on_click=on_method_selected,
            ),
            id="methods_scroll",
            width=1,
            height=4,
            hide_on_single_page=True,
        ),
        Back(Const("⬅️ Назад")),
        state=TopupSG.select_method,
        getter=getter_select_method,
    ),
    Window(
        Format(
            "⭐ <b>Оплата звёздами</b>\n\n"
            "Сумма: <b>{dialog_data[amount]} руб.</b>\n",
            when=F["dialog_data"]["payment_method"]
            == PaymentMethod.TELEGRAM_STARS.value,
        ),
        Url(
            Const("⭐ Оплатить звёздами"),
            url=Format("{dialog_data[invoice_link]}"),
            when=F["dialog_data"]["payment_method"]
            == PaymentMethod.TELEGRAM_STARS.value,
        ),
        Format(
            "💳 Переведите <b>{dialog_data[amount]} руб.</b> на карту:\n"
            "<code>{dialog_data[card_number]}</code>\n\n"
            "В комментарии укажите код: <code>{dialog_data[reference]}</code>\n\n"
            "После перевода отправьте чек администратору.",
            when=F["dialog_data"]["payment_method"] == PaymentMethod.MANUAL_CARD.value,
        ),
        Cancel(Const("🏠 Главное меню")),
        state=TopupSG.waiting_payment,
    ),
)
