from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.region import RegionDTO
from src.application.mediator import Mediator
from src.application.use_cases.region.get_by_id import IdRegionRequest


@inject
async def getter_metadata_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data

    if "metadata_loaded" not in data:
        region_id: int = dialog_manager.start_data["region_id"]
        region: RegionDTO = await mediator.handle(
            IdRegionRequest(region_id=region_id)
        )
        m = region.metadata
        data["region_id"] = region_id
        data["tg_group_url"] = m.tg_group_url or ""
        data["vk_group_url"] = m.vk_group_url or ""
        data["max_channel_url"] = m.max_channel_url or ""
        data["metadata_loaded"] = True

    return {
        "tg_group_url": data["tg_group_url"] or "— не задано",
        "vk_group_url": data["vk_group_url"] or "— не задано",
        "max_channel_url": data["max_channel_url"] or "— не задано",
    }