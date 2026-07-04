from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import SwitchTo, Cancel, Button
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.utils.text_validators import (
    capitalize_word,
    validate_phone_number,
)

from .getters import (
    getter_store_edit_start,
    getter_store_edit_confirm,
)
from .handlers import on_confirm_edit, on_next_confirm
from .states import StoreEditSG

store_edit_dialog = Dialog(
    Window(
        Format(
            "🏦 <b>Редактирование магазина</b>\n\n"
            "Текущие данные:\n"
            "🔰 <b>Название:</b> {shop_name}\n"
            "🌎 <b>Город:</b> {store_city}\n"
            "📲 <b>Телефон:</b> {store_phone}\n\n"
            "Выберите, что хотите изменить:"
        ),
        SwitchTo(
            Const("✏️ Изменить название"),
            id="edit_name",
            state=StoreEditSG.name,
        ),
        SwitchTo(
            Const("✏️ Изменить город"),
            id="edit_city",
            state=StoreEditSG.city,
        ),
        SwitchTo(
            Const("✏️ Изменить телефон"),
            id="edit_phone",
            state=StoreEditSG.phone,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_store_edit_start,
        state=StoreEditSG.start,
    ),
    Window(
        Format(
            "🔰 <b>Текущее название:</b> {shop_name}\n\n"
            "Введите новое название магазина:"
        ),
        TextInput(
            id="name",
            type_factory=capitalize_word,
            on_success=on_next_confirm,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_start",
            state=StoreEditSG.start,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_store_edit_start,
        state=StoreEditSG.name,
    ),
    Window(
        Format("🌎 <b>Текущий город:</b> {store_city}\n\nВведите новый город:"),
        TextInput(
            id="city",
            type_factory=capitalize_word,
            on_success=on_next_confirm,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_start",
            state=StoreEditSG.start,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_store_edit_start,
        state=StoreEditSG.city,
    ),
    Window(
        Format(
            "📲 <b>Текущий телефон:</b> {store_phone}\n\nВведите новый номер (с +7):"
        ),
        TextInput(
            id="phone",
            type_factory=validate_phone_number,
            on_success=on_next_confirm,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_start",
            state=StoreEditSG.start,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_store_edit_start,
        state=StoreEditSG.phone,
    ),
    Window(
        Format(
            "📋 <b>Проверьте изменения:</b>\n\n"
            "🔰 <b>Название:</b> {new_shop_name}\n"
            "🌎 <b>Город:</b> {new_city}\n"
            "📲 <b>Телефон:</b> {new_phone}\n\n"
            "Сохранить изменения?"
        ),
        Button(
            Const("✅ Сохранить"),
            id="confirm_edit",
            on_click=on_confirm_edit,
        ),
        SwitchTo(
            Const("❌ Отмена"),
            id="back_start",
            state=StoreEditSG.start,
            style=Style(style=ButtonStyle.DANGER),
        ),
        getter=getter_store_edit_confirm,
        state=StoreEditSG.confirm,
    ),
)
