from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.store.get_by_user import GetUserStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_store_edit_start(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    store: AdDTO = await mediator.handle(
        GetUserStoreRequest(user_id=user.id, region_id=user.region_id)
    )
    s = store.store_content

    dialog_manager.dialog_data["ad_id"] = store.id

    return {
        "shop_name": s.shop_name if s else "—",
        "store_city": s.city if s else "—",
        "store_phone": s.contacts.phone if s and s.contacts else "—",
    }


@inject
async def getter_store_edit_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    s = ad.store_content

    return {
        "new_shop_name": data.get("new_name") or (s.shop_name if s else "—"),
        "new_city": data.get("new_city") or (s.city if s else "—"),
        "new_phone": data.get("phone")
        or (s.contacts.phone if s and s.contacts else "—"),
    }
