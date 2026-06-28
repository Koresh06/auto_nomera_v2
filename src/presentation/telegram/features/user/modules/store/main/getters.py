from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.ad import AdDTO
from src.application.dtos.user import UserDTO
from src.application.exceptions.ad import AdNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.store.get_by_user import GetUserStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest


@inject
async def getter_store_main(
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
    if store is None:
        raise AdNotFoundException()

    dialog_manager.dialog_data["ad_id"] = store.id

    s = store.store_content
    items = s.items if s else ()

    return {
        "store_name": s.shop_name if s else "—",
        "store_city": s.city if s else "—",
        "store_phone": s.contacts.phone if s and s.contacts else "—",
        "numbers_count": len(items),
        "user_balance": user.balance_display,
    }