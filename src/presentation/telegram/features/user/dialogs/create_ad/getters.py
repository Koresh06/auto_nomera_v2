from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from src.application.dtos.calendar import CalendarDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.slots.get_calendar import GetCalendarRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType


REGION_ID_DEV = 1


async def getter_default_ad(dialog_manager: DialogManager, **kwargs) -> dict:
    start_data = dialog_manager.start_data or {}
    ad_type = start_data.get("ad_type")  # type: ignore
    dialog_manager.dialog_data["ad_type"] = ad_type
    return {
        "ad_type": ad_type,
        "is_sale": ad_type == AdType.SALE,
        "is_buy": ad_type == AdType.BUY,
        "is_urgent": ad_type == AdType.URGENT_BUYOUT,
    }


async def getter_media_plate(dialog_manager: DialogManager, **kwargs) -> dict:
    photo = dialog_manager.dialog_data.get("photo")
    media = None
    if photo:
        media = MediaAttachment(
            file_id=MediaId(
                file_id=photo["file_id"],
                file_unique_id=photo["file_unique_id"],
            ),
            type=ContentType.PHOTO,
        )
    dialog_manager.dialog_data["media"] = media

    return {
        "media": media,
        "photo": bool(photo),
    }


@inject
async def getter_user_phone(
    dialog_manager: DialogManager, 
    mediator: FromDishka[Mediator], 
    **kwargs
) -> dict:
    tg_id = dialog_manager.event.from_user.id

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=tg_id)
    )
    dialog_manager.dialog_data["current_phone"] = user.phone
    return {"phone": user.phone}


@inject
async def calendar_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
):
    cal: CalendarDTO = await mediator.handle(
        GetCalendarRequest(region_id=REGION_ID_DEV)
    )
    # ожидаем: cal.slots -> list[dict] с ключами id/text/is_busy
    return {"slots": cal.slots}
