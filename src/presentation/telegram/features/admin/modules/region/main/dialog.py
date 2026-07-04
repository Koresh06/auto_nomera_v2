from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import Start, Column, Select, Row, Button, Back, Cancel
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.admin.modules.region.create.states import (
    CreateRegionSG,
)
from .states import MainRegionSG
from .handlers import (
    on_open_edit_metadata,
    on_open_edit_settings,
    on_region_selected,
    on_toggle_status,
)
from .getters import getter_region_detail, getter_region_list

main_region_dialog = Dialog(
    Window(
        Const("🗺 <b>Управление регионами</b>"),
        Start(
            Const("📋 Список регионов"),
            id="region_list",
            state=MainRegionSG.list,
        ),
        Start(
            Const("➕ Создать регион"),
            id="region_create",
            state=CreateRegionSG.title,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MainRegionSG.start,
    ),
    Window(
        Const("📋 <b>Список регионов</b>\n\nВыберите регион:"),
        Column(
            Select(
                Format("{item[0]}"),
                id="region_select",
                item_id_getter=lambda item: item[1],
                items="regions",
                on_click=on_region_selected,
            ),
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MainRegionSG.list,
        getter=getter_region_list,
    ),
    Window(
        Multi(
            Format("🗺 <b>{region.title}</b>\n"),
            Format("Статус: {status_label}"),
            Format("Часовой пояс: <i>{region.timezone.value}</i>"),
            Format(
                "Канал: @{region.channel_username} (<code>{region.channel_id}</code>)"
            ),
            Const(""),
            Format("⏰ Слоты: {slot_times_str}"),
            Format("📅 Календарь слотов: {days_range} дн. вперёд"),
            Format("💰 Системно-платных слотов: {system_paid_slots_count}"),
            Format("🔒 Лимит публикаций: {publication_limit_enabled}"),
            Format("💵 Цена платного слота: {paid_slot_price} руб."),
            sep="\n",
        ),
        Row(
            Button(
                Format("{status_label}  (нажми, чтобы переключить)"),
                id="toggle_status",
                on_click=on_toggle_status,
            ),
        ),
        Row(
            Button(
                Const("✏️ Настройки слотов"),
                id="edit_settings",
                on_click=on_open_edit_settings,
            ),
            Button(
                Const("🔗 Соцсети/каналы"),
                id="edit_metadata",
                on_click=on_open_edit_metadata,
            ),
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MainRegionSG.detail,
        getter=getter_region_detail,
    ),
)
