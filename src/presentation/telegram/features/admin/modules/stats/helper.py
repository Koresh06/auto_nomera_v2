from enum import Enum
from typing import Callable
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Row, Button
from aiogram_dialog.widgets.text import Format

from src.domain.enums.period import StatsPeriod


def period_flags(period: StatsPeriod) -> dict:
    return {
        "is_today": period == StatsPeriod.TODAY,
        "is_week": period == StatsPeriod.WEEK,
        "is_month": period == StatsPeriod.MONTH,
        "is_all": period == StatsPeriod.ALL,
        "lbl_today": ("🟢 " if period == StatsPeriod.TODAY else "") + "Сегодня",
        "lbl_week": ("🟢 " if period == StatsPeriod.WEEK else "") + "Неделя",
        "lbl_month": ("🟢 " if period == StatsPeriod.MONTH else "") + "Месяц",
        "lbl_all": ("🟢 " if period == StatsPeriod.ALL else "") + "Всё",
    }


def period_row(on_period_selected: Callable) -> Row:
    return Row(
        Button(Format("{lbl_today}"), id="today", on_click=on_period_selected),
        Button(Format("{lbl_week}"), id="week", on_click=on_period_selected),
        Button(Format("{lbl_month}"), id="month", on_click=on_period_selected),
        Button(Format("{lbl_all}"), id="all", on_click=on_period_selected),
    )


class ScopePrivate(str, Enum):
    GENERAL = "general"
    REGION = "region"


def _current_period(dialog_manager: DialogManager, scope: ScopePrivate) -> StatsPeriod:
    raw = dialog_manager.dialog_data.get(
        f"period_{scope.value}", StatsPeriod.MONTH.value
    )
    return StatsPeriod(raw)
