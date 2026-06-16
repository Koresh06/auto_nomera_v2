from datetime import datetime, timezone

from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_start_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    title_region = None
    if user.region_id is not None:
        try:
            region: RegionDTO = await mediator.handle(
                IdRegionRequest(user.region_id)
            )
            title_region = region.title
        except RegionNotFoundException:
            title_region = None

    now = datetime.now(timezone.utc)
    has_pre_publication = (
        user.pre_publication_expires_at is not None
        and user.pre_publication_expires_at > now
    )

    return {
        "user": user,
        "title_region": title_region,
        "has_pre_publication": has_pre_publication,
    }

@inject
async def list_regions_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict[str, list[RegionDTO]]:
    regions: list[RegionDTO] = await mediator.handle(GetRegionsRequest())
    return {"regions": regions}


async def getter_user_menu(dialog_manager: DialogManager, **kwargs) -> dict:
    return {
        "is_store": True,
        "region_name": "Москва",
        "is_early_access": True,
    }