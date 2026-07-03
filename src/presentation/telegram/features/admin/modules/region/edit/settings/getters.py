from datetime import time

from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.mediator import Mediator
from src.application.dtos.region import RegionDTO
from src.application.use_cases.region.get_by_id import IdRegionRequest


SLOT_TIME_CANDIDATES: tuple[time, ...] = (
    time(8, 0), time(10, 0), time(12, 0), time(14, 0),
    time(16, 0), time(18, 0), time(20, 0), time(22, 0),
)

@inject
async def getter_settings_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.start_data["region_id"]
    region: RegionDTO = await mediator.handle(IdRegionRequest(region_id=region_id))
    s = region.settings

    dialog_manager.dialog_data["publication_limit_enabled"] = s.publication_limit_enabled
    dialog_manager.dialog_data["slot_times"] = [t.strftime("%H:%M") for t in s.slot_times]

    return {
        "slot_times_str": ", ".join(t.strftime("%H:%M") for t in s.slot_times),
        "days_range": s.days_range,
        "system_paid_slots_count": s.system_paid_slots_count,
        "limit_label": "✅ Да" if s.publication_limit_enabled else "❌ Нет",
        "paid_slot_price": str(s.paid_slot_price),
    }


async def getter_slot_times(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    selected = set(dialog_manager.dialog_data.get("slot_times", []))
    candidates = [
        {
            "id": t.strftime("%H:%M"),
            "label": f"{'✅' if t.strftime('%H:%M') in selected else '⬜'} {t.strftime('%H:%M')}",
        }
        for t in SLOT_TIME_CANDIDATES
    ]
    return {"candidates": candidates}