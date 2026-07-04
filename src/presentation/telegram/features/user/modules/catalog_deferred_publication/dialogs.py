from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Start, Button, Select, ScrollingGroup, Back
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.modules.catalog_deferred_publication.handlers import (
    on_catalog_item_selected,
    on_delete_catalog_item,
)
from src.presentation.telegram.widgets.custom_scroll import CatalogScroll

from .states import CatalogDeferredPublishSG
from .getters import getter_catalog_list, getter_urgent_catalog

catalog_deferred_publication_dialog = Dialog(
    Window(
        Const(
            "💎 <b>Каталог срочных выкупов и объявлений до публикации</b>\n\n"
            "😔 В вашем регионе пока нет новых заявок.\n"
            "🚀 Объявления до публикации появятся за 2 часа до размещения в канале.",
            when=~F["has_ads"],
        ),
        DynamicMedia("current_media", when=F["has_ads"]),
        Format("{card.ad_text}", when=F["has_ads"]),
        Format(
            "\n🕐 <b>Дата публикации:</b> {card.pub_time}",
            when=F["has_ads"] & F["card"].pub_time,
        ),
        CatalogScroll(
            id="catalog_scroll",
            view_state=CatalogDeferredPublishSG.list_view,
            when=F["has_ads"],
        ),
        Button(
            Const("🗑 Удалить"),
            id="delete_current_ad",
            on_click=on_delete_catalog_item,
            when=F["is_admin"] & F["has_ads"],
        ),
        Start(
            Const("🏠 Главное меню"),
            id="general_menu",
            state=UserMenuSG.menu,
            mode=StartMode.RESET_STACK,
        ),
        state=CatalogDeferredPublishSG.start,
        getter=getter_urgent_catalog,
        disable_web_page_preview=True,
    ),
    Window(
        Const("📋 <b>Список объявлений:</b>\n"),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),
                id="catalog_select",
                item_id_getter=lambda x: x[1],
                items="catalog_buttons",
                on_click=on_catalog_item_selected,
            ),
            id="catalog_list_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
        ),
        Const("😔 Список пуст.", when=~F["has_ads"]),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CatalogDeferredPublishSG.list_view,
        getter=getter_catalog_list,
    ),
)
