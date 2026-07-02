from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Select,
    Button,
    Back,
    Cancel,
    Column,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput

from src.presentation.telegram.features.admin.modules.region.edit.states import (
    EditRegionSettingsSG,
)
from src.presentation.telegram.features.error_handlers import on_input_error
from .getters import (
    getter_settings_menu,
    getter_slot_times,
)
from .handlers import (
    on_days_range_success,
    on_paid_slot_price_success,
    on_reset_defaults,
    on_settings_confirm,
    on_slot_time_toggle,
    on_slot_times_done,
    on_system_paid_count_success,
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
        Row(
            Button(
                Const("✅ Сохранить"),
                id="confirm",
                on_click=on_settings_confirm,
            ),
            Cancel(Const("❌ Отмена")),
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
        Back(Const("⬅️ Назад")),
        state=EditRegionSettingsSG.slot_times,
        getter=getter_slot_times,
    ),
    Window(
        Format(
            "📅 <b>Календарь слотов</b>\n\n"
            "Текущее значение: {days_range} дн.\n"
            "Введите число от 1 до 31:"
        ),
        TextInput(
            id="days_range_input",
            type_factory=int,
            on_success=on_days_range_success,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
        ),
        state=EditRegionSettingsSG.days_range,
        getter=getter_settings_menu,
    ),
    Window(
        Format(
            "💰 <b>Системно-платные слоты</b>\n\n"
            "Текущее значение: {system_paid_slots_count}\n"
            "Введите количество:"
        ),
        TextInput(
            id="paid_count_input",
            type_factory=int,
            on_success=on_system_paid_count_success,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
        ),
        state=EditRegionSettingsSG.system_paid_slots_count,
        getter=getter_settings_menu,
    ),
    Window(
        Format(
            "💵 <b>Цена платного слота</b>\n\n"
            "Текущая цена: {paid_slot_price} ₽\n"
            "Введите новую цену:"
        ),
        TextInput(
            id="price_input",
            type_factory=float,
            on_success=on_paid_slot_price_success,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionSettingsSG.menu,
        ),
        state=EditRegionSettingsSG.paid_slot_price,
        getter=getter_settings_menu,
    ),
)
