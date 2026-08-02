from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Select,
    ScrollingGroup,
    Next,
    Cancel,
    Back,
    Row,
    PrevPage,
    NextPage,
    Button,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.admin.modules.stats.helper import period_row
from src.presentation.telegram.widgets.smart_scroll_text import SmartScrollingText

from .states import (
    StatsReplenishmentSG,
)
from .getters import (
    getter_general_stats,
    getter_regions_list,
    getter_region_stats,
    getter_region_detailed_payments,
)
from .handlers import (
    on_region_selected,
    on_period_selected,
)

stats_replenishment_dialog = Dialog(
    Window(
        Format(
            "💰 <b>Статистика пополнений</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "✅ Успешных оплат: <b>{total_count}</b>\n"
            "💵 Общая сумма: <b>{total_amount} руб.</b>\n"
            "⭐️ Stars: <b>{stars_total}</b>\n"
            "📍 Топ регион: <b>{top_region}</b>\n\n"
            "📊 По методам:\n{method_lines}"
        ),
        period_row(on_period_selected),
        Next(Const("📍 По регионам")),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StatsReplenishmentSG.general,
        getter=getter_general_stats,
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
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StatsReplenishmentSG.regions_list,
        getter=getter_regions_list,
    ),
    Window(
        Format(
            "📍 <b>{region_title}</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "✅ Успешных оплат: <b>{total_count}</b>\n"
            "💵 Сумма: <b>{total_amount} руб.</b>\n\n"
            "📊 По методам:\n{method_lines}"
        ),
        period_row(on_period_selected),
        Next(Const("📋 Детализация платежей")),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StatsReplenishmentSG.region_detail,
        getter=getter_region_stats,
    ),
    Window(
        Const("Пополнения отсутствуют", when=~F["cards"]),
        Const("📍 Пополнения по региону\n", when=F["cards"]),
        SmartScrollingText(
            text=Format("{cards}"),
            id="scroll_cards",
            items_per_page=5,
            when=F["cards"],
        ),
        Row(
            PrevPage(scroll="scroll_cards", text=Const("⬅️ Назад")),
            Button(Format("📄 {page_current} / {pages_total}"), id="paginator"),
            NextPage(scroll="scroll_cards", text=Const("➡️ Далее")),
            when=F["cards"],
        ),
        Back(Const("⬅️ Назад")),
        state=StatsReplenishmentSG.region_stats,
        getter=getter_region_detailed_payments,
    ),
)
