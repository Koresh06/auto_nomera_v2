from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    SwitchTo,
    Cancel,
    Select,
    ScrollingGroup,
    Back,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.widgets.custom_scroll import CatalogScroll
from src.presentation.telegram.features.admin.modules.stats.helper import period_row


from .states import PublishStatsSG
from .getters import (
    getter_admin_catalog_list,
    getter_admin_catalog,
    getter_pub_stats,
    getter_region_schedule,
    getter_schedule_regions,
)
from .handlers import (
    on_delete_deferred,
    on_open_deferred_catalog,
    on_period_selected,
    on_schedule_region_selected,
    on_catalog_item_selected,
)

publish_stats_dialog = Dialog(
    Window(
        Format(
            "📊 <b>Статистика публикаций</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "📦 Всего: <b>{total}</b>\n"
            "📍 Топ регион: <b>{top_region}</b>\n\n"
            "<b>По статусам:</b>\n{status_lines}\n\n"
            "<b>По типам:</b>\n{type_lines}"
        ),
        period_row(on_period_selected),
        SwitchTo(
            Const("🗓 Расписание по регионам"),
            id="to_schedule",
            state=PublishStatsSG.regions_list,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PublishStatsSG.stats,
        getter=getter_pub_stats,
    ),
    Window(
        Const("🗓 <b>Выберите регион:</b>", when="has_regions"),
        Const("Активных регионов нет", when=~F["has_regions"]),
        ScrollingGroup(
            Select(
                Format("{item.title}"),
                id="sched_region_select",
                items="regions",
                item_id_getter=lambda i: i.id,
                on_click=on_schedule_region_selected,
            ),
            id="sched_regions_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
            when="has_regions",
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PublishStatsSG.regions_list,
        getter=getter_schedule_regions,
    ),
    Window(
        Format("🗓 <b>Расписание — {region_title}</b>\n\n{legend}\n\n{schedule_text}"),
        Button(
            Const("📦 Каталог отложенных публикаций"),
            id="deferred_catalog",
            on_click=on_open_deferred_catalog,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PublishStatsSG.schedule,
        getter=getter_region_schedule,
        disable_web_page_preview=True,
    ),
    Window(
        Const("📦 Отложенных публикаций нет", when=~F["has_ads"]),
        DynamicMedia("current_media", when=F["current_media"]),
        Format(
            "{card.ad_text}\n\n"
            "🕒 Публикация: {card.pub_time}\n\n"
            "🎯 Услуги:\n{card.services_line}\n\n"
            "👤 {card.owner_link} | 🆔 <code>{card.owner_tg_id}</code>",
            when="has_ads",
        ),
        CatalogScroll(
            id="catalog_scroll",
            view_state=PublishStatsSG.list,
            when="has_ads",
        ),
        Button(
            Const("🗑 Отменить публикацию"),
            id="del",
            on_click=on_delete_deferred,
            when="has_ads",
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PublishStatsSG.catalog,
        getter=getter_admin_catalog,
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
        state=PublishStatsSG.list,
        getter=getter_admin_catalog_list,
    ),
)
