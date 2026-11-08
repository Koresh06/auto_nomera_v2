"""Что выбрал админ в конструкторе: период в dialog_data, разделы и регионы
в чекбоксах. Значения чекбоксов приходят из callback_data, поэтому разбираем
их только через белый список."""

from datetime import date

from aiogram_dialog import DialogManager

from src.application.dtos.stats_report import ReportFilter
from src.domain.enums.period import StatsPeriod
from src.domain.enums.report import ReportSection
from src.domain.value_objects.date_range import DateRange

SECTIONS_WIDGET = "export_sections"
REGIONS_WIDGET = "export_regions"
CUSTOM_PERIOD = "custom"
DEFAULT_SECTIONS = (ReportSection.SUMMARY, ReportSection.REGIONS)


def selected_sections(manager: DialogManager) -> tuple[ReportSection, ...]:
    checked = set(manager.find(SECTIONS_WIDGET).get_checked())
    return tuple(s for s in ReportSection if s.value in checked)


def selected_region_ids(manager: DialogManager) -> tuple[int, ...]:
    checked = manager.find(REGIONS_WIDGET).get_checked()
    return tuple(sorted(int(rid) for rid in checked if rid.isdigit()))


def _custom_range(manager: DialogManager) -> DateRange:
    data = manager.dialog_data
    return DateRange(
        start=date.fromisoformat(data["date_from"]),
        end=date.fromisoformat(data["date_to"]),
    )


def period_label(manager: DialogManager) -> str:
    period = manager.dialog_data.get("period", StatsPeriod.MONTH.value)
    if period == CUSTOM_PERIOD:
        return _custom_range(manager).label
    return StatsPeriod(period).label()


def report_filter(manager: DialogManager) -> ReportFilter:
    period = manager.dialog_data.get("period", StatsPeriod.MONTH.value)
    if period == CUSTOM_PERIOD:
        since, until = _custom_range(manager).bounds_utc()
        return ReportFilter(
            since_utc=since, until_utc=until, region_ids=selected_region_ids(manager)
        )
    return ReportFilter(
        since_utc=StatsPeriod(period).since_utc(),
        region_ids=selected_region_ids(manager),
    )
