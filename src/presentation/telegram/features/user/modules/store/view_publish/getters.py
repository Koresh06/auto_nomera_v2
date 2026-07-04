from datetime import date, time

from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.store.get_by_user import GetUserStoreRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.domain.value_objects.slot_key import SlotKey


@inject
async def getter_store_preview(
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
    items = s.items if s else ()

    result_lines = (
        "\n".join(f"✖️ {item.plate} ➖ {item.price.display}" for item in items) or "—"
    )

    dialog_manager.dialog_data["ad_id"] = store.id
    dialog_manager.dialog_data["ad_type"] = store.ad_type

    return {
        "store_name": s.shop_name if s else "—",
        "store_city": s.city if s else "—",
        "contacts": s.contacts.display if s and s.contacts else "—",
        "result_lines": result_lines,
        "has_items": len(items) > 0,
    }


@inject
async def getter_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    start_data = dialog_manager.start_data or {}

    ad_id: int = data.get("ad_id") or start_data.get("ad_id")
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    s = ad.store_content
    items = s.items if s else ()
    result_lines = (
        "\n".join(f"✖️ {item.plate} ➖ {item.price.display}" for item in items) or "—"
    )

    slot_raw = start_data.get("slot")
    if slot_raw:
        data["slot_region_id"] = slot_raw["region_id"]
        data["slot_day"] = slot_raw["slot_day"]
        data["slot_time"] = slot_raw["slot_time"]
        data["is_paid"] = start_data.get("is_paid", True)

    slot = None
    if "region_id" in data:
        slot = SlotKey(
            region_id=data["region_id"],
            local_day=date.fromisoformat(data["slot_day"]),
            local_time=time.fromisoformat(data["slot_time"]),
        )

    return {
        "store_name": s.shop_name if s else "—",
        "store_city": s.city if s else "—",
        "contacts": s.contacts.display if s and s.contacts else "—",
        "result_lines": result_lines,
        "slot_day": slot.date_display if slot else "",
        "slot_time": slot.time_display if slot else "",
    }
