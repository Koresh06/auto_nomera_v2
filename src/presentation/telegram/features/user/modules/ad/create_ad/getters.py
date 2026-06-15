from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from src.application.dtos.ad import AdDTO
from src.application.dtos.calendar import CalendarDTO
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
from src.application.use_cases.slots.get_calendar import GetCalendarRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.presentation.telegram.utils import build_media_attachment


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

    dialog_manager.dialog_data["user"] = user
    dialog_manager.dialog_data["region_id"] = region.id
    dialog_manager.dialog_data["channel_username"] = region.channel_username
    dialog_manager.dialog_data["region_title"] = region.title

    return {
        "ad_type": ad_type,
        "is_sale": ad_type == AdType.SALE,
        "is_buy": ad_type == AdType.BUY,
        "is_urgent": ad_type == AdType.URGENT_BUYOUT,
    }


async def getter_duplicate_ad(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    existing_ad: AdDTO = data["existing_ad"]
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
    user: UserDTO = dialog_manager.dialog_data["user"]
    dialog_manager.dialog_data["current_phone"] = user.phone
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
    user: UserDTO = data["user"]
    channel_username: str = data["channel_username"]

    slot: SlotKey | None = data.get("slot")

    if data.get("reuse_ad"):
        existing_ad: AdDTO = data["existing_ad"]
        c = existing_ad.content
        plate = c.plate_number if c else ""
        city = c.city if c else ""
        price = c.price.display if c else ""
        contacts = c.contacts.display if c else ""
        media = data.get("media") or build_media_attachment(
            c.image_file_id if c else None
        )
        data["media"] = media

    else:
        plate = data.get("plate")
        city = dialog_manager.find("city").get_value()
        price_raw = data["price"]
        phone = data.get("phone") or data.get("current_phone", "")
        contacts = Contacts.from_user(username=user.username, phone=phone).display
        price = Price.format(price_raw)

        media = data.get("media")
        if not media:
            media = await mediator.handle(
                EnsureAdImageRefRequest(
                    plate=plate,
                    channel_username=channel_username,
                    chat_id=tg_id,
                )
            )
            data["media"] = media

        data["city"] = city
        data["price"] = price_raw
        data["phone"] = phone

    return {
        "plate": plate,
        "city": city,
        "price": price,
        "contacts": contacts,
        "slot_day": slot.date_display if slot else "",
        "slot_time": slot.time_display if slot else "",
        "media": media,
    }


@inject
async def getter_publication_service(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = dialog_manager.dialog_data["user"]
    pub_id: int = dialog_manager.dialog_data["publication_id"]

    services: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest(is_active=True)
    )

    # получаем уже купленные услуги для этой публикации
    pub: PublicationDTO = await mediator.handle(
        GetPublicationByIdRequest(publication_id=pub_id)
    )
    bought_types: set[PublicationServiceType] = {
        s.type
        for s in pub.services
        if s.status
        in (
            PublicationServiceStatus.ACTIVE,
            PublicationServiceStatus.USED,
        )
    }

    ORDER = {
        PublicationServiceType.PRIORITY_PUBLISH: 1,
        PublicationServiceType.HIGHLIGHT: 2,
        PublicationServiceType.PIN: 3,
        PublicationServiceType.AUTOPUBLISH: 4,
    }

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=pub.ad_id))

    # фильтруем
    filtered = [
        s
        for s in services
        if s.type != PublicationServiceType.PRE_PUBLICATION
        and not (
            ad
            and ad.ad_type == AdType.STORE
            and s.type == PublicationServiceType.HIGHLIGHT
        )
    ]

    # сортируем
    filtered.sort(key=lambda s: ORDER.get(s.type, 99))

    # формируем отображение
    display = [
        (
            (
                f"{s.title} ✅"
                if s.type.value in bought_types
                else f"{s.title} — {s.price // 100} руб."
            ),
            s.type.value,
        )
        for s in filtered
    ]

    return {
        "available_services": display,
        "balance": f"{user.balance:.0f} руб.",
    }


async def getter_finish(dialog_manager: DialogManager, **kwargs) -> dict:
    data = dialog_manager.dialog_data
    slot: SlotKey = data["slot"]

    return {
        "is_auto_pub": False,
        "media": data["media"],
        "slot_day": slot.date_display,
        "slot_time": slot.time_display,
        "channel_username": data["channel_username"],
        "region_title": data["region_title"],
        "selected_services": "Заглушка",
    }
