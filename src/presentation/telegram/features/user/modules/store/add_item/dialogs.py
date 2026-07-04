from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Start, Column, Back
from aiogram_dialog.widgets.style import Style

from src.domain.services.ad.store_validator import parse_store_validator
from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.modules.store.edit_items.states import (
    StoreEditItemsSG,
)
from src.presentation.telegram.features.user.modules.store.main.states import (
    StoreMainSG,
)
from src.presentation.telegram.features.user.modules.store.view_publish.states import (
    StoreViewPublishSG,
)
from .states import StoreAddItemsSG
from .handlers import on_confirm_save, on_input_submit
from .getters import add_items_getter

store_add_items_dialog = Dialog(
    Window(
        Format(
            "✍🏻 <b>Добавление номеров в Ваш магазин.</b>\n"
            "<b>Указать можно не более {approx_max} шт.</b>\n\n"
            "‼️ <b>Введите номер и его стоимость, каждый номер — с новой строки.</b>\n"
            "⚠️ <b>Внимание:</b> цена <b>не может быть равна 0</b> или отсутствовать!\n\n"
            "📌 <b>Примеры:</b>\n\n"
            "<code>x111xx01-1000000</code>\n"
            "<code>о100оо01-500000</code>\n"
            "<code>к101хх01-30000</code>\n"
        ),
        TextInput(
            id="items_input",
            type_factory=parse_store_validator,
            on_success=on_input_submit,
            on_error=on_input_error,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=add_items_getter,
        state=StoreAddItemsSG.enter,
    ),
    Window(
        Format(
            "🧾 <b>Проверьте введённые номера:</b>\n\n"
            "{result_lines}\n\n"
            "<i>Добавлено: {added_count}. "
            "Отклонено (из-за лимита в посте {approx_max} шт.): {skipped_count}.</i>\n\n"
            "Если всё верно — нажмите <b>✅ Сохранить</b>, "
            "иначе вернитесь для исправления."
        ),
        Button(
            Const("✅ Сохранить"),
            id="save_items",
            on_click=on_confirm_save,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        getter=add_items_getter,
        state=StoreAddItemsSG.preview,
    ),
    Window(
        Format(
            "🥳 <b>Поздравляем! Номера добавлены в Ваш магазин:</b>\n\n"
            "{result_lines}\n\n"
            "<i>Добавлено: {added_count}. "
            "Отклонено (из-за лимита в посте {approx_max} шт.): {skipped_count}.</i>"
        ),
        Column(
            Start(
                Const("📣 Просмотр и Публикация"),
                id="view_publish",
                state=StoreViewPublishSG.preview,
            ),
            Start(
                Const("✍🏻 Редактировать"),
                id="go_edit",
                state=StoreEditItemsSG.all_list,
            ),
            Start(
                Const("🏦 Мой магазин"),
                id="my_store",
                state=StoreMainSG.main,
            ),
            Start(
                Const("🏠 Главное меню"),
                id="menu",
                state=UserMenuSG.menu,
            ),
        ),
        getter=add_items_getter,
        state=StoreAddItemsSG.result,
    ),
)
