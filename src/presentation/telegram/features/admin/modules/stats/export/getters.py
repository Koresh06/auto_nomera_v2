from decimal import Decimal
from html import escape

from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.stats_report import ReportPreviewDTO
from src.application.mediator import Mediator
from src.application.services.stats_report.sections import SECTIONS
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.stats.report import GetReportPreviewRequest
from src.core.config import settings
from src.domain.enums.period import StatsPeriod
from src.domain.enums.report import ReportSection
from src.presentation.telegram.features.admin.modules.stats.helper import period_flags

from .selection import (
    CUSTOM_PERIOD,
    period_label,
    report_filter,
    selected_region_ids,
    selected_sections,
)

_MAX_LISTED_REGIONS = 5


def _money(value: Decimal | None) -> str:
    return f"{value or 0:,.2f}".replace(",", " ")


def _count(value: Decimal | None) -> int:
    return int(value or 0)


def _regions_label(titles: dict[int, str], selected: tuple[int, ...]) -> str:
    if not selected:
        return "все"
    if len(selected) > _MAX_LISTED_REGIONS:
        return f"выбрано {len(selected)}"
    return ", ".join(escape(titles.get(rid, f"#{rid}")) for rid in selected)


def _section_items() -> list[dict]:
    return [{"id": s.value, "title": SECTIONS[s].title} for s in ReportSection]


@inject
async def getter_export_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    regions = await mediator.handle(GetRegionsRequest())
    sections = selected_sections(dialog_manager)
    return {
        "period_label": period_label(dialog_manager),
        "regions_label": _regions_label(
            {r.id: r.title for r in regions}, selected_region_ids(dialog_manager)
        ),
        "sections_label": ", ".join(SECTIONS[s].title for s in sections)
        or "не выбраны",
        "personal_hidden": (
            dialog_manager.event.from_user.id not in settings.telegram.admin_ids
        ),
    }


async def getter_export_period(dialog_manager: DialogManager, **kwargs) -> dict:
    period = dialog_manager.dialog_data.get("period", StatsPeriod.MONTH.value)
    is_custom = period == CUSTOM_PERIOD
    preset = StatsPeriod.MONTH if is_custom else StatsPeriod(period)
    flags = period_flags(preset)
    if is_custom:
        # подсвечена только кнопка своих дат, а не запасной пресет
        flags = {k: v.removeprefix("🟢 ") for k, v in flags.items() if k[:3] == "lbl"}
    return {
        **flags,
        "lbl_custom": ("🟢 " if is_custom else "") + "📆 Свои даты",
    }


@inject
async def getter_export_regions(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    return {"regions": await mediator.handle(GetRegionsRequest())}


async def getter_export_sections(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"sections": _section_items()}


@inject
async def getter_export_preview(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    sections = selected_sections(dialog_manager)
    preview: ReportPreviewDTO = await mediator.handle(
        GetReportPreviewRequest(
            report_filter=report_filter(dialog_manager), sections=sections
        )
    )
    t = preview.totals
    row_lines = "\n".join(
        f"  {SECTIONS[section].title}: <b>{count}</b>"
        for section, count in preview.row_counts.items()
    )
    return {
        "period_label": period_label(dialog_manager),
        "revenue": _money(t.get("revenue_total")),
        "purchases": _count(t.get("revenue_count")),
        "revenue_slot": _money(t.get("revenue_slot")),
        "revenue_service": _money(t.get("revenue_publication_service")),
        "revenue_pre": _money(t.get("revenue_pre_publication")),
        "from_balance": _money(t.get("revenue_from_balance")),
        "inflow": _money(t.get("inflow_total")),
        "topups": _money(t.get("topup_total")),
        "users_new": _count(t.get("users_new")),
        "users_total": _count(t.get("users_total")),
        "ads_new": _count(t.get("ads_new")),
        "publications": _count(t.get("publications_total")),
        "services": _count(t.get("services_total")),
        "row_lines": f"\n📑 <b>Строк в разделах</b>\n{row_lines}" if row_lines else "",
    }
