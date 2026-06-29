from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.user import UserDTO
from src.application.exceptions.ad import AdNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.store.get_by_user import GetUserStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.services.ad.store_validator import MAX_ITEMS



@inject
async def add_items_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    store: AdDTO = await mediator.handle(
        GetUserStoreRequest(user_id=user.id, region_id=user.region_id)
    )
    if store is None:
        raise AdNotFoundException()
    ad_id = store.id
    data["ad_id"] = ad_id

    parsed_items: list[dict] = data.get("parsed_items", [])
    skipped_count: int = data.get("skipped_count", 0)

    if parsed_items:
        result_lines = "\n".join(
            f"✖️ {item['plate']} ➖ {item['price_display']}"
            for item in parsed_items
        )
        added_count = len(parsed_items)
    else:
        result_lines = "—"
        added_count = 0

    return {
        "approx_max": MAX_ITEMS,
        "result_lines": result_lines,
        "added_count": added_count,
        "skipped_count": skipped_count,
    }