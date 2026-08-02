from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.global_stats import AdTypeCountDTO, GlobalStatsDTO
from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.stats.globals import GetGlobalStatsRequest
from src.domain.enums.ad import AdType
from src.domain.enums.period import StatsPeriod
from src.presentation.telegram.features.admin.modules.stats.helper import (
    ScopePrivate,
    _current_period,
    period_flags,
)


def build_ads_type_lines(by_ad_type: list[AdTypeCountDTO]) -> str:
    counts_by_type = {t.ad_type: t.count for t in by_ad_type}
    return "\n".join(
        f"✖️ {AdTypeCountDTO(ad_type=t, count=counts_by_type.get(t, 0)).label}: "
        f"<b>{counts_by_type.get(t, 0)}</b>"
        for t in (AdType.SALE, AdType.BUY, AdType.URGENT_BUYOUT, AdType.STORE)
    )


@inject
async def getter_global_stats(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    period: StatsPeriod = _current_period(dialog_manager, ScopePrivate.GENERAL)
    stats: GlobalStatsDTO = await mediator.handle(GetGlobalStatsRequest(period=period))
    regions = await mediator.handle(GetRegionsRequest())

    top_regions_lines = (
        "\n".join(f"📍 {r.title}: {r.count}" for r in stats.top_regions) or "—"
    )

    return {
        "stats": stats,
        "regions": regions,
        "period_label": period.label(),
        "ads_type_lines": build_ads_type_lines(stats.by_ad_type),
        "top_regions_lines": top_regions_lines,
        "total_amount": stats.amount_display,
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
async def getter_region_global_stats(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    period: StatsPeriod = _current_period(dialog_manager, ScopePrivate.REGION)
    region_id = dialog_manager.dialog_data["region_id"]

    region = await mediator.handle(IdRegionRequest(region_id=region_id))
    stats: GlobalStatsDTO = await mediator.handle(
        GetGlobalStatsRequest(period=period, region_id=region_id)
    )

    services_lines = (
        "\n".join(
            f"✖️ {s.label}: <b>{s.count}</b>"
            for s in sorted(stats.by_service, key=lambda x: x.count, reverse=True)
        )
        or "—"
    )

    top = stats.top_service

    return {
        "stats": stats,
        "region": region,
        "period_label": period.label(),
        "ads_type_lines": build_ads_type_lines(stats.by_ad_type),
        "services_lines": services_lines,
        "most_used_service": top.label if top else "—",
        "total_amount": stats.amount_display,
        **period_flags(period),
    }
