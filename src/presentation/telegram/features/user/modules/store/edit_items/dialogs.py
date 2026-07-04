from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import (
    ScrollingGroup,
    Select,
    Row,
    SwitchTo,
    Button,
    Cancel,
    Back,
)
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.error_handlers import on_input_error

from .getters import getter_confirm_item, getter_item, getter_store_items
from .handlers import (
    on_confirm_update,
    on_delete_item,
    on_edit_item_selected,
    on_plate_input,
    on_price_input,
)
from .states import StoreEditItemsSG

store_edit_items_dialog = Dialog(
    Window(
        Const("📋 Номера отсутствуют", when=~F["items"]),
        Format(
            "✍🏻 <b>Редактирование номеров магазина.</b>\n\n"
            "Выберите номер для редактирования:",
            when="items",
        ),
        ScrollingGroup(
            Select(
                Format("🚘 {item.plate} — {item.price.display}"),
                id="item_select",
                items="items",
                item_id_getter=lambda i: i.plate,
                on_click=on_edit_item_selected,
            ),
            id="scroll_items",
            width=1,
            height=10,
            hide_on_single_page=True,
            when="items",
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_store_items,
        state=StoreEditItemsSG.all_list,
    ),
    Window(
        Format(
            "🚘 <b>Номер:</b> {plate}\n💰 <b>Цена:</b> {price}\n\nВыберите действие:"
        ),
        Row(
            SwitchTo(
                Const("✏️ Изменить номер"),
                id="edit_plate",
                state=StoreEditItemsSG.edit_plate,
            ),
            SwitchTo(
                Const("✏️ Изменить цену"),
                id="edit_price",
                state=StoreEditItemsSG.edit_price,
            ),
        ),
        Button(
            Const("🗑 Удалить"),
            id="delete_item",
            on_click=on_delete_item,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_item,
        state=StoreEditItemsSG.edit,
    ),
    Window(
        Format(
            "✏️ <b>Изменение номера</b>\n"
            "Текущий: <code>{plate}</code>\n\n"
            "Введите новый номер:\n"
            "📌 Пример: <code>А123ВВ161</code>"
        ),
        TextInput(
            id="new_plate",
            type_factory=str,
            on_success=on_plate_input,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_edit",
            state=StoreEditItemsSG.edit,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_item,
        state=StoreEditItemsSG.edit_plate,
    ),
    Window(
        Format(
            "💰 <b>Изменение цены</b>\n"
            "Текущая: <b>{price}</b>\n\n"
            "Введите новую цену (только цифры):\n\n"
            "📌 Примеры:\n"
            "➡️ <code>1000</code>\n"
            "➡️ <code>500000</code>"
        ),
        TextInput(
            id="new_price",
            type_factory=str,
            on_success=on_price_input,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_edit",
            state=StoreEditItemsSG.edit,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_item,
        state=StoreEditItemsSG.edit_price,
    ),
    Window(
        Format(
            "🧾 <b>Проверьте изменения:</b>\n\n"
            "🔄 Новый номер: <code>{new_plate}</code>",
            when=F["new_plate"],
        ),
        Format(
            "🧾 <b>Проверьте изменения:</b>\n\n💰 Новая цена: <b>{new_price}</b> руб.",
            when=F["new_price"],
        ),
        Button(
            Const("✅ Сохранить"),
            id="confirm_update",
            on_click=on_confirm_update,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_edit",
            state=StoreEditItemsSG.edit,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=getter_confirm_item,
        state=StoreEditItemsSG.confirm,
    ),
)
