from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Select,
    Button,
    Back,
    Cancel,
    Column,
    SwitchTo,
    Group,
)
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.error_handlers import on_input_error

from .states import PaidServiceAdminSG

from .getters import getter_service_list, getter_service_detail
from .handlers import (
    on_field_update,
    on_reset_default,
    on_service_selected,
    on_toggle_status,
)

paid_service_admin_dialog = Dialog(
    Window(
        Const("💎 <b>Платные услуги</b>\n\nВыберите услугу:"),
        Column(
            Select(
                Format("{item[0]}"),
                id="service_select",
                item_id_getter=lambda item: item[1],
                items="services",
                on_click=on_service_selected,
            ),
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.list,
        getter=getter_service_list,
    ),
    Window(
        Multi(
            Format("<b>{service.title}</b>\n"),
            Format("Статус: {status_label}"),
            Format("💵 Цена: {price_display}"),
            Format("⏱ Длительность: {duration_display}"),
            Const(""),
            Format("📝 Описание:\n{description_display}"),
            sep="\n",
        ),
        Button(
            Format("{toggle_label}"),
            id="toggle_status",
            on_click=on_toggle_status,
        ),
        Group(
            SwitchTo(
                Const("💵 Изменить цену"),
                id="edit_price",
                state=PaidServiceAdminSG.edit_price,
            ),
            SwitchTo(
                Const("⏱ Изменить длительность"),
                id="edit_duration",
                state=PaidServiceAdminSG.edit_duration,
                when="has_duration",
            ),
            SwitchTo(
                Const("📝 Изменить описание"),
                id="edit_description",
                state=PaidServiceAdminSG.edit_description,
            ),
            SwitchTo(
                Const("✏️ Изменить название"),
                id="edit_title",
                state=PaidServiceAdminSG.edit_title,
            ),
            width=2,
        ),
        Button(
            Const("♻️ Сбросить к стандартным"),
            id="reset_default",
            on_click=on_reset_default,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.detail,
        getter=getter_service_detail,
    ),
    Window(
        Format(
            "💵 <b>Изменение цены</b>\n\n"
            "Текущая: {price_display}\n"
            "Введите новую цену (руб.):"
        ),
        TextInput(
            id="price_input",
            on_success=on_field_update,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.edit_price,
        getter=getter_service_detail,
    ),
    Window(
        Format(
            "⏱ <b>Изменение длительности</b>\n\n"
            "Текущая: {duration_display}\n"
            "Введите количество дней:"
        ),
        TextInput(
            id="duration_input",
            on_success=on_field_update,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.edit_duration,
        getter=getter_service_detail,
    ),
    Window(
        Format(
            "📝 <b>Изменение описания</b>\n\n"
            "Текущее: {description_display}\n\n"
            "Введите новое описание (или <code>-</code> чтобы очистить):"
        ),
        TextInput(
            id="description_input",
            on_success=on_field_update,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.edit_description,
        getter=getter_service_detail,
    ),
    Window(
        Format(
            "✏️ <b>Изменение названия</b>\n\n"
            "Текущее: {service.title}\n"
            "Введите новое название:"
        ),
        TextInput(id="title_input", on_success=on_field_update),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceAdminSG.edit_title,
        getter=getter_service_detail,
    ),
)
