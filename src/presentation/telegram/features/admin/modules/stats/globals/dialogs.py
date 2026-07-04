from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Next,
    Cancel,
    Back,
    Select,
    ScrollingGroup,
)
from aiogram_dialog.widgets.text import Const, Format

from src.presentation.telegram.features.admin.modules.stats.helper import period_row

from .states import GlobalStatsSG
from .getters import (
    getter_global_stats,
    getter_region_global_stats,
    getter_regions_list,
)
from .handlers import on_region_selected, on_period_selected

global_stats_dialog = Dialog(
    Window(
        Format(
            "📊 <b>Общая статистика</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "👥 <b>Пользователи</b>\n"
            "  Всего: <b>{stats.total_users}</b>\n"
            "  С магазином: <b>{stats.users_with_store}</b>\n"
            "  Без магазина: <b>{stats.users_without_store}</b>\n\n"
            "📣 <b>Объявления</b>\n"
            "  Всего: <b>{stats.total_ads}</b>\n"
            "  В очереди: <b>{stats.scheduled_ads}</b>\n"
            "{ads_type_lines}\n\n"
            "🌍 Регионов: <b>{stats.total_regions}</b>\n\n"
            "💰 <b>Финансы</b>\n"
            "  Покупок: <b>{stats.total_purchases}</b>\n"
            "  Сумма: <b>{total_amount} ₽</b>"
        ),
        period_row(on_period_selected),
        Next(Const("📍 По регионам")),
        Cancel(Const("⬅️ Назад")),
        state=GlobalStatsSG.start,
        getter=getter_global_stats,
    ),
    Window(
        Const("📍 <b>Выберите регион:</b>"),
        ScrollingGroup(
            Select(
                Format("{item.title}"),
                id="region_select",
                items="regions",
                item_id_getter=lambda item: item.id,
                on_click=on_region_selected,
            ),
            id="regions_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
        ),
        Back(Const("⬅️ Назад")),
        state=GlobalStatsSG.regions_list,
        getter=getter_regions_list,
    ),
    Window(
        Format(
            "📍 <b>{region.title}</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "👥 <b>Пользователи</b>\n"
            "  Всего: <b>{stats.total_users}</b>\n"
            "  С магазином: <b>{stats.users_with_store}</b>\n"
            "  Без магазина: <b>{stats.users_without_store}</b>\n\n"
            "📣 <b>Объявления</b>\n"
            "  Всего: <b>{stats.total_ads}</b>\n"
            "  В очереди: <b>{stats.scheduled_ads}</b>\n"
            "{ads_type_lines}\n\n"
            "💰 <b>Финансы</b>\n"
            "  Покупок: <b>{stats.total_purchases}</b>\n"
            "  Сумма: <b>{total_amount} ₽</b>\n\n"
            "💎 <b>Услуги</b>\n"
            "  Популярная: <b>{most_used_service}</b>\n"
            "  Всего: <b>{stats.total_services}</b>\n"
            "{services_lines}"
        ),
        period_row(on_period_selected),
        Back(Const("⬅️ Назад")),
        state=GlobalStatsSG.region_stats,
        getter=getter_region_global_stats,
    ),
)
