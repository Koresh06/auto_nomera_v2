from datetime import date, time

from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication_service.get_all import GetAllServicesRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.presentation.telegram.utils.build_media import build_media_attachment


@inject
async def getter_default_ad(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    start_data = dialog_manager.start_data or {}
    ad_type = start_data.get("ad_type")  # type: ignore
    dialog_manager.dialog_data["ad_type"] = ad_type

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))

    # dialog_manager.dialog_data["user"] = user
    dialog_manager.dialog_data["region_id"] = region.id
    dialog_manager.dialog_data["channel_username"] = region.channel_username
    dialog_manager.dialog_data["region_title"] = region.title

    return {
        "ad_type": ad_type,
        "is_sale": ad_type == AdType.SALE,
        "is_buy": ad_type == AdType.BUY,
        "is_urgent": ad_type == AdType.URGENT_BUYOUT,
    }

@inject
async def getter_duplicate_ad(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    existing_ad_id: int = data["existing_ad_id"]

    existing_ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=existing_ad_id))
    c = existing_ad.content

    media = build_media_attachment(c.image_file_id if c else None)

    return {
        "plate": c.plate_number if c else "",
        "city": c.city if c else "",
        "price": c.price.display if c else "",
        "contacts": c.contacts.display if c else "",
        "media": media,
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
    dialog_manager.dialog_data["media_file_id"] = media.file_id.file_id if media and media.file_id else None

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
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    dialog_manager.dialog_data["current_phone"] = user.phone
    return {"phone": user.phone}



@inject
async def getter_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    start_data = dialog_manager.start_data or {}
    tg_id = dialog_manager.event.from_user.id

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    if "ad_id" in start_data:
        ad_id: int = start_data["ad_id"]
        ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))

        c = ad.content
        plate = c.plate_number if c else ""
        city = c.city if c else ""
        price_raw = c.price.value if c else 0
        price = c.price.display if c else ""
        contacts = c.contacts.display if c else ""
        media: MediaAttachment | None = build_media_attachment(c.image_file_id if c else None)

        slot_raw = start_data.get("slot")
        slot = None
        if slot_raw:
            slot = SlotKey(
                region_id=slot_raw["region_id"],
                local_day=date.fromisoformat(slot_raw["slot_day"]),
                local_time=time.fromisoformat(slot_raw["slot_time"]),
            )
            data["region_id"] = slot_raw["region_id"]
            data["slot_day"] = slot_raw["slot_day"]
            data["slot_time"] = slot_raw["slot_time"]

        data["ad_id"] = ad_id
        data["ad_type"] = ad.ad_type.value if hasattr(ad.ad_type, "value") else ad.ad_type
        data["region_id"] = user.region_id
        data["plate"] = plate
        data["city"] = city
        data["price"] = price_raw
        data["phone"] = c.contacts.phone if c and c.contacts else ""
        data["media_file_id"] = media.file_id.file_id if media and media.file_id else None
        data["is_paid"] = start_data.get("is_paid", True)
        data["from_existing_draft"] = True

        return {
            "plate": plate,
            "city": city,
            "price": price,
            "contacts": contacts,
            "slot_day": slot.date_display if slot else "",
            "slot_time": slot.time_display if slot else "",
            "media": media,
        }

    
    channel_username: str = data["channel_username"]

    ad_type_raw = data.get("ad_type")
    needs_slot = ad_type_raw != AdType.URGENT_BUYOUT.value
    
    slot = None
    if needs_slot:
        slot = SlotKey(
            region_id=data["region_id"],
            local_day=date.fromisoformat(data["slot_day"]),
            local_time=time.fromisoformat(data["slot_time"]),
        )

    if data.get("reuse_ad"):
        existing_ad_id = data["existing_ad_id"] 
        existing_ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=existing_ad_id))
        c = existing_ad.content
        plate = c.plate_number if c else ""
        city = c.city if c else ""
        price_raw = c.price.value if c else 0
        price = c.price.display if c else ""
        contacts = c.contacts.display if c else ""
        phone = c.contacts.phone if c else ""

        media: MediaAttachment | None = build_media_attachment(c.image_file_id if c else None)
        data["media_file_id"] = media.file_id.file_id if media and media.file_id else None
    else:
        plate = data.get("plate")
        city = dialog_manager.find("city").get_value()
        price_raw = data["price"]
        phone = data.get("phone") or data.get("current_phone", "")
        contacts = Contacts.from_user(username=user.username, phone=phone).display
        price = Price.format(price_raw)

        media: MediaAttachment = await mediator.handle(
            EnsureAdImageRefRequest(
                plate=plate,
                channel_username=channel_username,
                chat_id=tg_id,
            )
        )
        data["media_file_id"] = media.file_id.file_id if media and media.file_id else None

    data["phone"] = phone
    data["price"] = price_raw
    data["city"] = city


    return {
        "plate": plate,
        "city": city,
        "price": price,
        "contacts": contacts,
        "slot_day": slot.date_display if slot else "",
        "slot_time": slot.time_display if slot else "",
        "media": media,
    }


