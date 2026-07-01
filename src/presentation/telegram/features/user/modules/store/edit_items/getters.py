from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.store.get_by_user import GetUserStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_store_items(
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
    items = list(s.items) if s else []

    dialog_manager.dialog_data["ad_id"] = store.id
    
    return {"items": items}


@inject
async def getter_item(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    plate: str = data["selected_plate"]

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    s = ad.store_content

    price_display = "—"
    if s:
        for item in s.items:
            if item.plate == plate:
                price_display = item.price.display
                data["selected_price_value"] = item.price.value
                break

    return {
        "plate": plate,
        "price": price_display,
    }

@inject
async def getter_confirm_item(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    return {
        "new_plate": data.get("new_plate"),
        "new_price": data.get("new_price_display"),
    }