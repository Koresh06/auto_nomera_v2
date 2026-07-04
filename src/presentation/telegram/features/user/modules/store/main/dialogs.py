from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Column, Start

from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.modules.store.add_item.states import (
    StoreAddItemsSG,
)
from src.presentation.telegram.features.user.modules.store.edit_items.states import (
    StoreEditItemsSG,
)
from src.presentation.telegram.features.user.modules.store.edit_store.states import (
    StoreEditSG,
)
from src.presentation.telegram.features.user.modules.store.main.getters import (
    getter_store_main,
)
from src.presentation.telegram.features.user.modules.store.view_publish.states import (
    StoreViewPublishSG,
)
from .states import StoreMainSG


store_main_dialog = Dialog(
    Window(
        Format(
            "🏦 <b>Магазин</b>\n\n"
            "<b>🔰 Название:</b> {store_name}\n"
            "<b>🌎 Город:</b> {store_city}\n"
            "<b>📲 Телефон:</b> {store_phone}\n"
            "<b>🚘 Номеров в продаже:</b> {numbers_count} шт.\n"
            "<b>💰 Ваш баланс:</b> {user_balance}"
        ),
        Column(
            Start(
                Const("📣 Просмотр и Публикация"),
                id="view_publish",
                state=StoreViewPublishSG.preview,
            ),
            Start(
                Const("✅ Добавить номера"),
                id="add_items",
                state=StoreAddItemsSG.enter,
            ),
            Start(
                Const("✍🏻 Редактировать номера"),
                id="edit_items",
                state=StoreEditItemsSG.all_list,
            ),
            Start(
                Const("📝 Редактировать магазин"),
                id="edit_store",
                state=StoreEditSG.start,
            ),
            Start(
                Const("🏠 Главное меню"),
                id="menu",
                state=UserMenuSG.menu,
            ),
        ),
        getter=getter_store_main,
        state=StoreMainSG.main,
    )
)
