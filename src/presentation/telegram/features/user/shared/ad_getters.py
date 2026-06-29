from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.ad import AdDTO
from src.application.dtos.calendar import CalendarDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication_service.get_all import GetAllServicesRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.slots.get_calendar import GetCalendarRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType
from src.domain.enums.publication_service import PublicationServiceStatus, PublicationServiceType
from src.presentation.telegram.utils.build_media import build_media_attachment


@inject
async def calendar_getter(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    cal: CalendarDTO = await mediator.handle(
        GetCalendarRequest(region_id=user.region_id)
    )

    available = [s for s in cal.slots if not s.disabled]

    return {"slots": available}


@inject
async def getter_publication_service(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    start_data = dialog_manager.start_data or {}
    pub_id: int = dialog_manager.dialog_data.get("publication_id") or start_data.get("publication_id")

    services: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest(is_active=True)
    )

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

    filtered.sort(key=lambda s: ORDER.get(s.type, 99))

    display = [
        (
            (
                f"{s.title} ✅"
                if s.type.value in bought_types
                else f"{s.title} — {s.price} руб."
            ),
            s.type.value,
        )
        for s in filtered
    ]

    return {
        "available_services": display,
        "balance": user.balance_display,
    }


@inject
async def getter_finish(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    start_data = dialog_manager.start_data or {}

    pub_id: int = data.get("publication_id") or start_data.get("publication_id")
    data["publication_id"] = pub_id

    pub: PublicationDTO = await mediator.handle(
        GetPublicationByIdRequest(publication_id=pub_id)
    )
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=pub.ad_id))
    region: RegionDTO = await mediator.handle(IdRegionRequest(ad.region_id))

    slot = pub.slot

    active_services = [
        s
        for s in pub.services
        if s.status in (PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED)
    ]

    if active_services:
        selected_services = ",\n".join(
            PublicationServiceType(s.type).display for s in active_services
        )
    else:
        selected_services = "Нет"

    media_file_id = data.get("media_file_id") or (ad.content.image_file_id if ad.content else None)

    return {
        "is_auto_pub": False,
        "media": build_media_attachment(media_file_id),
        "slot_day": slot.date_display if slot else "—",
        "slot_time": slot.time_display if slot else "—",
        "channel_username": data.get("channel_username") or region.channel_username,
        "region_title": data.get("region_title") or region.title,
        "selected_services": selected_services,
    }