from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from src.application.dtos.calendar import CalendarDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.slots.get_calendar import GetCalendarRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType
from src.domain.value_objects.price import Price


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
    **kwargs,
) -> dict:
    tg_id = dialog_manager.event.from_user.id
    
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    dialog_manager.dialog_data["current_phone"] = user.phone
    dialog_manager.dialog_data["user"] = user
    return {"phone": user.phone}


@inject
async def calendar_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = dialog_manager.dialog_data["user"]

    cal: CalendarDTO = await mediator.handle(
        GetCalendarRequest(region_id=user.region_id)
    )
    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))

    dialog_manager.dialog_data["region_id"] = region.id
    dialog_manager.dialog_data["channel_username"] = region.channel_username

    available = [s for s in cal.slots if not s.disabled]

    return {"slots": available}


@inject
async def getter_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    tg_id = dialog_manager.event.from_user.id
    plate = data.get("plate")
    city = dialog_manager.find("city").get_value()
    price = dialog_manager.find("price").get_value() or data["price"]
    phone = data.get("phone") or data.get("")
    slot_day = data.get("slot_day")
    slot_time = data.get("slot_time")
    channel_username = data["channel_username"]

    media = data.get("media")
    if not media:
        media: MediaAttachment = await mediator.handle(
            EnsureAdImageRefRequest(
                plate=plate,
                channel_username=channel_username,
                chat_id=tg_id,
            )
        )
        dialog_manager.dialog_data["media"] = media

    dialog_manager.dialog_data["city"] = city
    dialog_manager.dialog_data["price"] = price
    dialog_manager.dialog_data["phone"] = phone

    return {
        "plate": plate,
        "city": city,
        "price": Price.format(price),
        "phone": phone,
        "slot_day": slot_day,
        "slot_time": slot_time,
        "media": media,
    }
