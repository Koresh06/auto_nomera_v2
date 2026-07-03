from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Select,
    Row,
    ScrollingGroup,
    SwitchTo,
    Cancel,
    Back,
)
from aiogram_dialog.widgets.text import Const, Format

from .states import (
    StatsReplenishmentSG,
)
from .getters import (
    getter_general_stats,
    getter_regions_list,
    getter_region_stats,
)
from .handlers import (
    on_period_selected,
    on_region_selected,
)


def _period_row():
    return Row(
        Button(Format("{lbl_today}"), id="today", on_click=on_period_selected),
        Button(Format("{lbl_week}"), id="week", on_click=on_period_selected),
        Button(Format("{lbl_month}"), id="month", on_click=on_period_selected),
        Button(Format("{lbl_all}"), id="all", on_click=on_period_selected),
    )


stats_replenishment_dialog = Dialog(
    Window(
        Format(
            "💰 <b>Статистика пополнений</b>\n"
            "📅 Период: <b>{period_label}</b>\n\n"
            "✅ Успешных оплат: <b>{total_count}</b>\n"
            "💵 Общая сумма: <b>{total_amount} руб.</b>\n"
            "🏆 Топ метод: <b>{top_method}</b>\n"
            "📍 Топ регион: <b>{top_region}</b>\n\n"
            "📊 По методам:\n{method_lines}"
        ),
        _period_row(),
        SwitchTo(
            Const("📍 По регионам"),
            id="to_regions",
            state=StatsReplenishmentSG.regions_list,
        ),
        Cancel(Const("⬅️ Назад")),
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
        Back(Const("⬅️ Назад")),
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
        _period_row(),
        Back(Const("⬅️ Назад")),
        state=StatsReplenishmentSG.region_detail,
        getter=getter_region_stats,
    ),
)
