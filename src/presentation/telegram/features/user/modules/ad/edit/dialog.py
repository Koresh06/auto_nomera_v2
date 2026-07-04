from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    ScrollingGroup,
    Select,
    Cancel,
    Back,
    Group,
    Button,
)
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.features.user.modules.ad.edit.getters import (
    getter_confirm_edit,
    getter_detail,
    getter_edit_field,
    getter_list_publications,
)
from src.presentation.telegram.features.user.modules.ad.edit.handlers import (
    on_apply_edit,
    on_delete_ad,
    on_edit_city,
    on_edit_phone,
    on_edit_plate,
    on_edit_price,
    on_field_input,
    on_select_publication,
)

from .states import EditAdSG

edit_ad_dialog = Dialog(
    Window(
        Const("📝 <b>Мои объявления</b>\n\n", when="publications"),
        Const("📋 У вас пока нет объявлений", when=~F["publications"]),
        ScrollingGroup(
            Select(
                Format("{item.display_title} — {item.slot_display}"),
                id="pub_select",
                item_id_getter=lambda p: p.id,
                items="publications",
                on_click=on_select_publication,
            ),
            id="pubs_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
            when="publications",
        ),
        Cancel(Const("🏠 Главное меню")),
        state=EditAdSG.list,
        getter=getter_list_publications,
    ),
    Window(
        DynamicMedia("media", when=F["media"]),
        Format(
            "{type_ad}\n\n"
            "🌎<b>Город:</b> {city}\n"
            "🚘<b>Номер:</b> {plate}\n"
            "💰<b>Цена:</b> {price}\n"
            "📲<b>Связь:</b> {contacts}\n"
        ),
        Group(
            Button(
                Const("🚘 Изменить номер"),
                id="edit_plate",
                on_click=on_edit_plate,
                when="can_edit_plate",
            ),
            Button(
                Const("🌎 Изменить город"),
                id="edit_city",
                on_click=on_edit_city,
            ),
            Button(
                Const("💰 Изменить цену"),
                id="edit_price",
                on_click=on_edit_price,
            ),
            Button(
                Const("📲 Изменить телефон"),
                id="edit_phone",
                on_click=on_edit_phone,
            ),
            width=2,
        ),
        Button(
            Const("🗑 Удалить"),
            id="delete_ad",
            on_click=on_delete_ad,
            when=~F["start_data"]["back_to_finish"],
        ),
        Back(
            Const("⬅️ Назад"),
            when=~F["start_data"]["back_to_finish"],
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        Cancel(
            Const("⬅️ Назад"),
            when=F["start_data"]["back_to_finish"],
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditAdSG.detail,
        getter=getter_detail,
    ),
    Window(
        Format("{edit_label}"),
        TextInput(
            id="field_input",
            type_factory=str,
            on_success=on_field_input,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditAdSG.edit_field,
        getter=getter_edit_field,
    ),
    Window(
        Format(
            "⚠️ <b>Подтвердите изменение</b>\n\n"
            "{field_label}: <b>{new_value}</b>\n\n"
            "Изменения применятся сразу после подтверждения."
        ),
        Button(
            Const("✅ Применить"),
            id="apply_edit",
            on_click=on_apply_edit,
        ),
        Back(Const("❌ Отмена")),
        state=EditAdSG.confirm_edit,
        getter=getter_confirm_edit,
    ),
)
