from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_start_menu(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict[str, UserDTO]:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    return {"user": user}


@inject
async def list_regions_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict[str, RegionDTO]:
    regions: RegionDTO = await mediator.handle(GetRegionsRequest())
    return {"regions": regions}
