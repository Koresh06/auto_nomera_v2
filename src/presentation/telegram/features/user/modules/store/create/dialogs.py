from aiogram.types import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.kbd import (
    Column,
    Button,
    Cancel,
    Back,
    Start,
    Next,
    RequestContact,
)
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory

from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.features.user.modules.ad.create_ad.getters import (
    getter_user_phone,
)
from src.presentation.telegram.features.user.modules.ad.create_ad.handlers import (
    on_phone_input_success,
    on_phone_received_contact,
)
from src.presentation.telegram.features.user.modules.store.create.handlers import (
    on_finish,
)
from src.presentation.telegram.features.user.modules.store.main.states import (
    StoreMainSG,
)
from src.presentation.telegram.utils.text_validators import (
    capitalize_word,
    validate_phone_number,
)
from .states import StoreCreateSG
from .validators import validate_store
from .getters import (
    getter_current_region_user,
    getter_finish_store,
)

create_store_dialog = Dialog(
    Window(
        Format(
            "🗂 Создание Вашего магазина.\n\n"
            "⚠️ Создать магазин в регионе {region_name} можно только если у Вас более 5 постоянных объявлений "
            "или Вы являетесь профессиональным продавцом.\n\n"
            "Вы действительно хотите создать магазин?"
        ),
        Column(
            Next(Const("✅ Да")),
            Cancel(Const("✖️ Нет")),
        ),
        state=StoreCreateSG.confirm_create,
        getter=getter_current_region_user,
    ),
    Window(
        Const("🏦 <b>Введите название Вашего магазина:</b>"),
        TextInput(
            id="name",
            on_success=Next(),
            type_factory=validate_store,
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=StoreCreateSG.name,
    ),
    Window(
        Const(
            "🌎 <b>Укажите город (без сокращений), в котором находится Ваш магазин:</b>"
        ),
        TextInput(
            id="city",
            on_success=Next(),
            type_factory=capitalize_word,
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=StoreCreateSG.city,
    ),
    Window(
        Const(
            "📞 <b>Укажите Ваш номер телефона (с 8 или +7, без пробелов и лишних символов):</b>\n\n"
            "<b>Можно также отправить контакт кнопкой ниже.</b>"
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
        Next(Format("{phone}"), when="phone"),
        Back(Const("⬅️ Назад")),
        markup_factory=ReplyKeyboardFactory(
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        state=StoreCreateSG.phone,
        getter=getter_user_phone,
    ),
    Window(
        Format(
            "📋 Данные Вашего магазина:\n\n"
            "🔰 <b> Название:</b> {shop_name}\n"
            "🌏 <b> Город:</b> {city}\n"
            "📲 <b>Связь</b>: {contacts}\n\n"
            "Подтвердить создание магазина?"
        ),
        Button(
            Const("✅ Подтвердить"),
            id="confirm_finish",
            on_click=on_finish,
        ),
        Back(Const("⬅️ Назад")),
        state=StoreCreateSG.confirm_store,
        getter=getter_finish_store,
    ),
    Window(
        Format(
            '🥳 <b>Поздравляем! Ваш магазин "{dialog_data[shop_name]}" успешно создан.</b>\n\n'
            "Теперь у Вас есть возможность добавлять и публиковать номера не по одному, а сразу одним списком."
        ),
        Start(
            Const("🏦 Мой магазин"),
            id="my_store",
            state=StoreMainSG.main,
        ),
        state=StoreCreateSG.message_final,
    ),
)
