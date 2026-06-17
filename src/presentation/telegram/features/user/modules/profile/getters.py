from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.count_ads_by_user import CountAdsByUserRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def profile_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
):
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))
    count_ads: int = await mediator.handle(
        CountAdsByUserRequest(
            user_id=user.id,
            region_id=user.region_id,
        )
    )

    return {
        "user": user,
        "region": region,
        "count_ads": count_ads,
    }
