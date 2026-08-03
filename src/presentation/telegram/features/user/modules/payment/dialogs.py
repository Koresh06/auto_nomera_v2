from aiogram import F
from aiogram.enums import ButtonStyle, ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.kbd import (
    Back,
    Cancel,
    RequestContact,
    Url,
    Column,
    Button,
)
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory

from src.domain.enums.payment import PaymentMethod
from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.utils.text_validators import validate_phone_number

from .states import PaymentSG
from .getters import getter_select_payment_method
from .handlers import (
    on_payment_method_selected,
    on_phone_input_success,
    on_phone_received_contact,
)

payment_dialog = Dialog(
    Window(
        Format(
            "💳 <b>Оплата</b>\n\n"
            "{description}\n\n"
            "Сумма: <b>{amount} руб.</b>\n\n"
            "Выберите способ оплаты:"
        ),
        # ScrollingGroup(
        #     Select(
        #         Format("{item[title]}"),
        #         id="method_select",
        #         items="methods",
        #         item_id_getter=lambda it: it["id"],
        #         on_click=on_payment_method_selected,
        #     ),
        #     id="methods_scroll",
        #     width=1,
        #     height=4,
        #     hide_on_single_page=True,
        # ),
        Column(
            Button(
                Const("💳 СБП / Банк карты / ЮMoney"),
                id="method_yookassa",
                on_click=on_payment_method_selected,
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            Button(
                Const("⭐ TG Stars"),
                id="method_stars",
                on_click=on_payment_method_selected,
            ),
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaymentSG.select_method,
        getter=getter_select_payment_method,
    ),
    Window(
        Format(
            "⚠️ <b>Выбирайте оплату - СБП</b>\n\nСумма: <b>{dialog_data[amount]} руб.</b>",
            when=F["dialog_data"]["payment_method"] == PaymentMethod.YOOKASSA.value,
        ),
        Url(
            Const("Оплатить"),
            url=Format("{dialog_data[confirmation_url]}"),
            when=F["dialog_data"]["payment_method"] == PaymentMethod.YOOKASSA.value,
        ),
        Format(
            "⭐ <b>Оплата звёздами</b>\n\nСумма: <b>{dialog_data[amount]} руб.</b>",
            when=F["dialog_data"]["payment_method"]
            == PaymentMethod.TELEGRAM_STARS.value,
        ),
        Url(
            Const("Оплатить"),
            url=Format("{dialog_data[invoice_link]}"),
            when=F["dialog_data"]["payment_method"]
            == PaymentMethod.TELEGRAM_STARS.value,
        ),
        # Format(
        #     "💳 Переведите <b>{dialog_data[amount]} руб.</b> на карту:\n"
        #     "<code>{dialog_data[card_number]}</code>\n\n"
        #     "В комментарии укажите код: <code>{dialog_data[reference]}</code>\n\n"
        #     "После перевода отправьте чек администратору.",
        #     when=F["dialog_data"]["payment_method"] == PaymentMethod.MANUAL_CARD.value,
        # ),
        Cancel(
            Const("Отменить"),
            style=Style(style=ButtonStyle.DANGER),
        ),
        state=PaymentSG.waiting_payment,
    ),
    Window(
        Const(
            "📱 <b>Нужен номер телефона</b>\n\n"
            "По закону (54-ФЗ) для формирования чека об оплате "
            "требуется контакт покупателя. Введите номер телефона "
            "в формате <b>+7XXXXXXXXXX</b> — на него придёт кассовый чек.\n\n"
            "Мы используем его только для чека."
        ),
        RequestContact(Const("📞 Отправить номер")),
        MessageInput(
            func=on_phone_received_contact,
            content_types=[ContentType.CONTACT],
        ),
        TextInput(
            id="phone",
            type_factory=validate_phone_number,
            on_success=on_phone_input_success,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        markup_factory=ReplyKeyboardFactory(
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        state=PaymentSG.waiting_phone,
    ),
)
