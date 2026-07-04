from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Select,
    Button,
    Cancel,
    Column,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.admin.modules.region.edit.states import (
    EditRegionSettingsSG,
)
from .getters import (
    getter_settings_menu,
    getter_slot_times,
)
from .handlers import (
    on_reset_defaults,
    on_settings_field_update,
    on_slot_time_toggle,
    on_slot_times_done,
    on_toggle_publication_limit,
)

edit_region_settings_dialog = Dialog(
    Window(
        Multi(
            Const("⚙️ <b>Настройки слотов</b>\n"),
            Format("⏰ Времена: {slot_times_str}"),
            Format("📅 Слоты на: {days_range} дн. вперёд"),
            Format("💰 Системно-платных: {system_paid_slots_count}"),
            Format("🔒 Лимит публикаций: {limit_label}"),
            Format("💵 Цена платного слота: {paid_slot_price} ₽"),
            sep="\n",
        ),
        Column(
            SwitchTo(
                Const("⏰ Изменить времена слотов"),
                id="edit_slot_times",
                state=EditRegionSettingsSG.slot_times,
            ),
            SwitchTo(
                Const("📅 Горизонт календаря"),
                id="edit_days_range",
                state=EditRegionSettingsSG.days_range,
            ),
            SwitchTo(
                Const("💰 Кол-во платных слотов"),
                id="edit_paid_count",
                state=EditRegionSettingsSG.system_paid_slots_count,
            ),
            SwitchTo(
                Const("💵 Цена платного слота"),
                id="edit_price",
                state=EditRegionSettingsSG.paid_slot_price,
            ),
            Button(
                Format("🔒 Лимит публикаций: {limit_label}"),
                id="toggle_limit",
                on_click=on_toggle_publication_limit,
            ),
        ),
        Button(
            Const("♻️ По умолчанию"),
            id="reset_defaults",
            on_click=on_reset_defaults,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionSettingsSG.menu,
        getter=getter_settings_menu,
    ),
    Window(
        Const("⏰ <b>Времена публикации</b>\n\nВыберите нужные:"),
        Column(
            Select(
                Format("{item[label]}"),
                id="slot_time_select",
                item_id_getter=lambda item: item["id"],
                items="candidates",
                on_click=on_slot_time_toggle,
            ),
        ),
        Button(
            Const("✅ Готово"),
            id="slot_times_done",
            on_click=on_slot_times_done,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionSettingsSG.slot_times,
        getter=getter_slot_times,
    ),
    Window(
        Format(
            "📅 <b>Горизонт календаря</b>\n\nТекущее: {days_range} дн.\nВведите число от 1 до 31:"
        ),
        TextInput(
            id="days_range_input",
            type_factory=str,
            on_success=on_settings_field_update,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionSettingsSG.days_range,
        getter=getter_settings_menu,
    ),
    Window(
        Format(
            "💰 <b>Системно-платные слоты</b>\n\nТекущее: {system_paid_slots_count}\nВведите количество:"
        ),
        TextInput(
            id="paid_count_input",
            type_factory=str,
            on_success=on_settings_field_update,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionSettingsSG.system_paid_slots_count,
        getter=getter_settings_menu,
    ),
    Window(
        Format(
            "💵 <b>Цена платного слота</b>\n\nТекущая: {paid_slot_price} ₽\nВведите новую цену:"
        ),
        TextInput(
            id="price_input",
            type_factory=str,
            on_success=on_settings_field_update,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionSettingsSG.paid_slot_price,
        getter=getter_settings_menu,
    ),
)
