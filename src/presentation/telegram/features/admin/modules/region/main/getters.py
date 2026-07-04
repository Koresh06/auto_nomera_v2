from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.region import RegionDTO
from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.domain.entities.region import RegionStatus


@inject
async def getter_region_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    regions: list[RegionDTO] = await mediator.handle(GetRegionsRequest())
    return {
        "regions": [
            (f"{'🟢' if r.status == RegionStatus.ACTIVE else '🔴'} {r.title}", r.id)
            for r in regions
        ],
    }


@inject
async def getter_region_detail(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.dialog_data["region_id"]
    region: RegionDTO = await mediator.handle(IdRegionRequest(region_id=region_id))

    s = region.settings
    slot_times_str = ", ".join(t.strftime("%H:%M") for t in s.slot_times)

    return {
        "region": region,
        "is_active": region.is_active,
        "status_label": region.status_label,
        "slot_times_str": slot_times_str,
        "days_range": s.days_range,
        "system_paid_slots_count": s.system_paid_slots_count,
        "publication_limit_enabled": region.publication_limit_enabled_label,
        "paid_slot_price": str(s.paid_slot_price),
    }
