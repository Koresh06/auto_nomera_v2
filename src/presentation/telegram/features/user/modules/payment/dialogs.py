from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Cancel, ScrollingGroup, Select, Url

from src.domain.enums.payment import PaymentMethod

from .states import PaymentSG
from .getters import getter_select_payment_method
from .handlers import on_payment_method_selected


payment_dialog = Dialog(
    Window(
        Format(
            "💳 <b>Оплата</b>\n\n"
            "{description}\n"
            "Сумма: <b>{amount} руб.</b>\n\n"
            "Выберите способ оплаты:"
        ),
        ScrollingGroup(
            Select(
                Format("{item[title]}"),
                id="method_select",
                items="methods",
                item_id_getter=lambda it: it["id"],
                on_click=on_payment_method_selected,
            ),
            id="methods_scroll",
            width=1,
            height=4,
            hide_on_single_page=True,
        ),
        Cancel(Const("⬅️ Назад")),
        state=PaymentSG.select_method,
        getter=getter_select_payment_method,
    ),
    Window(
        Format(
            "⭐ <b>Оплата звёздами</b>\n\nСумма: <b>{dialog_data[amount]} руб.</b>",
            when=F["dialog_data"]["payment_method"] == PaymentMethod.TELEGRAM_STARS.value,
        ),
        Url(
            Const("⭐ Оплатить звёздами"),
            url=Format("{dialog_data[invoice_link]}"),
            when=F["dialog_data"]["payment_method"] == PaymentMethod.TELEGRAM_STARS.value,
        ),
        Format(
            "💳 Переведите <b>{dialog_data[amount]} руб.</b> на карту:\n"
            "<code>{dialog_data[card_number]}</code>\n\n"
            "В комментарии укажите код: <code>{dialog_data[reference]}</code>\n\n"
            "После перевода отправьте чек администратору.",
            when=F["dialog_data"]["payment_method"] == PaymentMethod.MANUAL_CARD.value,
        ),
        Cancel(Const("❌ Отменить")),
        state=PaymentSG.waiting_payment,
    ),
)