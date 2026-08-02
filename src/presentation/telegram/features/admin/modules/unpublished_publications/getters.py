from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.mediator import Mediator
from src.application.use_cases.publication.get_overdue_unpublished import (
    GetOverdueUnpublishedRequest,
    OverdueAdItemDTO,
)


@inject
async def getter_overdue_slots(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    items: list[OverdueAdItemDTO] = await mediator.handle(
        GetOverdueUnpublishedRequest()
    )
    dialog_manager.dialog_data["overdue_items"] = [
        {
            "publication_id": i.publication_id,
            "plate_number": i.plate_number,
            "ad_type": i.ad_type.value,
            "ad_type_display": i.ad_type_display,
            "owner_username": i.owner_username,
            "owner_tg_id": i.owner_tg_id,
            "owner_link": i.owner_link,
            "local_time_label": i.local_time_label,
        }
        for i in items
    ]

    counts: dict[str, int] = {}
    for i in items:
        counts[i.local_time_label] = counts.get(i.local_time_label, 0) + 1

    slots = sorted(counts.items())

    return {
        "slots": slots,
        "has_slots": bool(slots),
    }
