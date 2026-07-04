from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.domain.enums.period import StatsPeriod
from src.application.dtos.region import RegionDTO
from src.application.dtos.payment_stats import PaymentStatsDTO
from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.stats.payment import GetPaymentStatsRequest
from src.presentation.telegram.features.admin.modules.stats.helper import period_flags


def _current_period(dialog_manager: DialogManager, scope: str) -> StatsPeriod:
    raw = dialog_manager.dialog_data.get(f"period_{scope}", StatsPeriod.MONTH.value)
    return StatsPeriod(raw)


@inject
async def getter_general_stats(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    period = _current_period(dialog_manager, "general")
    stats: PaymentStatsDTO = await mediator.handle(
        GetPaymentStatsRequest(period=period)
    )

    method_lines = (
        "\n".join(
            f"  {m.label}: <b>{m.count}</b> ({m.amount_display} руб.)"
            for m in sorted(stats.by_method, key=lambda x: x.amount, reverse=True)
        )
        or "  —"
    )

    top = stats.top_method
    top_region = stats.top_region

    return {
        "period_label": period.label(),
        "total_count": stats.total_count,
        "total_amount": f"{stats.total_amount:.0f}",
        "top_method": top.label if top else "—",
        "top_region": (
            f"{top_region.region_title} ({top_region.amount_display} руб.)"
            if top_region
            else "—"
        ),
        "method_lines": method_lines,
        **period_flags(period),
    }


@inject
async def getter_regions_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    regions = await mediator.handle(GetRegionsRequest())
    return {"regions": regions}


@inject
async def getter_region_stats(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id = dialog_manager.dialog_data["region_id"]
    period = _current_period(dialog_manager, "region")

    region: RegionDTO = await mediator.handle(IdRegionRequest(region_id=region_id))
    stats: PaymentStatsDTO = await mediator.handle(
        GetPaymentStatsRequest(period=period, region_id=region_id)
    )

    method_lines = (
        "\n".join(
            f"  {m.label}: <b>{m.count}</b> ({m.amount_display} руб.)"
            for m in sorted(stats.by_method, key=lambda x: x.amount, reverse=True)
        )
        or "  —"
    )

    return {
        "region_title": region.title,
        "period_label": period.label(),
        "total_count": stats.total_count,
        "total_amount": stats.total_amount_display,
        "method_lines": method_lines,
        **period_flags(period),
    }
