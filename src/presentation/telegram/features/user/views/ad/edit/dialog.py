from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    ScrollingGroup,
    Select,
    SwitchTo,
    Cancel,
    Back,
    Group,
    Button,
)

from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.features.user.views.ad.edit.getters import (
    getter_confirm_edit,
    getter_detail,
    getter_edit_field,
    getter_list_publications,
)
from src.presentation.telegram.features.user.views.ad.edit.handlers import (
    on_apply_edit,
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
                Format("{item.plate_number} — {item.slot_display}"),
                id="pub_select",
                item_id_getter=lambda p: p.id,
                items="publications",
                on_click=on_select_publication,
            ),
            id="pubs_scroll",
            width=1,
            height=8,
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
            "📲<b>Контакты:</b> {contacts}\n"
        ),
        Group(
            SwitchTo(
                Const("🚘 Изменить номер"),
                id="edit_plate",
                on_click=on_edit_plate,
                state=EditAdSG.edit_field,
                when="can_edit_plate",
            ),
            SwitchTo(
                Const("🌎 Изменить город"),
                id="edit_city",
                on_click=on_edit_city,
                state=EditAdSG.edit_field,
            ),
            SwitchTo(
                Const("💰 Изменить цену"),
                id="edit_price",
                on_click=on_edit_price,
                state=EditAdSG.edit_field,
            ),
            SwitchTo(
                Const("📲 Изменить телефон"),
                id="edit_phone",
                on_click=on_edit_phone,
                state=EditAdSG.edit_field,
            ),
            width=2,
        ),
        Back(Const("⬅️ Назад")),
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
        Back(Const("⬅️ Назад")),
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
