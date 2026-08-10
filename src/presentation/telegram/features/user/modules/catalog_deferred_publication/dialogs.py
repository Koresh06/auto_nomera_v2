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
from src.presentation.telegram.features.user.modules.paid_services.states import (
    PrePublicationSG,
)

from .states import CatalogDeferredPublishSG
from .getters import getter_catalog_list, getter_urgent_catalog

catalog_deferred_publication_dialog = Dialog(
    Window(
        Format(
            "💎 <b>Каталог срочных выкупов и объявлений до публикации</b>\n\n"
            "😔 В вашем регионе пока нет новых заявок.\n"
            "🚀 Объявления до публикации появятся за {pre_publication_window_hours} часа до размещения в канале.",
            when=F["has_subscription"] & ~F["has_ads"],
        ),
        Format(
            "<b>💎 Получайте первыми эксклюзивный доступ к объявлениям из раздела «Срочный выкуп», а также к новым объявлениям за {pre_publication_window_hours} часа до их публикации на канале.</b>",
            when=~F["has_subscription"],
        ),
        Const(
            "📋 <b>Список объявлений:</b>\n",
            when=F["has_subscription"] & F["has_ads"],
        ),
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
            when=F["has_subscription"],
        ),
        Start(
            Const("💎 Получить доступ"),
            id="go_to_paid_services",
            state=PrePublicationSG.confirm,
            when=~F["has_subscription"],
            style=Style(style=ButtonStyle.SUCCESS),
        ),
        Start(
            Const("🏠 Главное меню"),
            id="general_menu",
            state=UserMenuSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
            mode=StartMode.RESET_STACK,
        ),
        state=CatalogDeferredPublishSG.start,
        getter=getter_catalog_list,
    ),
    Window(
        DynamicMedia("current_media", when=F["current_media"]),
        Format("{card.ad_text}", when=F["has_ads"]),
        Format(
            "\n🕐 <b>Дата публикации:</b> {card.pub_time}",
            when=F["has_ads"] & F["card"].pub_time,
        ),
        CatalogScroll(
            id="catalog_scroll",
            view_state=CatalogDeferredPublishSG.start,
            when=F["has_ads"],
        ),
        Button(
            Const("🗑 Удалить"),
            id="delete_current_ad",
            on_click=on_delete_catalog_item,
            when=F["is_admin"] & F["has_ads"],
            style=Style(style=ButtonStyle.DANGER),
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CatalogDeferredPublishSG.details,
        getter=getter_urgent_catalog,
        disable_web_page_preview=True,
    ),
)
