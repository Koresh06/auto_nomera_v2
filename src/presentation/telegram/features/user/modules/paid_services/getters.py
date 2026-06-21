from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram_dialog import DialogManager

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.get_user import GetUserPublicationsRequest
from src.application.use_cases.publication_service.get_all import GetAllServicesRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)


@inject
async def getter_current_services(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id = dialog_manager.event.from_user.id
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    dialog_manager.dialog_data["user"] = user

    definitions: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )

    ORDER = {
        PublicationServiceType.PRE_PUBLICATION: 0,
        PublicationServiceType.PRIORITY_PUBLISH: 1,
        PublicationServiceType.HIGHLIGHT: 2,
        PublicationServiceType.PIN: 3,
        PublicationServiceType.AUTOPUBLISH: 4,
    }

    active_defs = sorted(
        (d for d in definitions if d.is_active),
        key=lambda d: ORDER.get(d.type, 99),
    )

    services = [
        {
            "name": d.title,
            "description": d.description or "",
            "duration_text": (
                f"{d.duration_days} дн."
                if d.duration_days
                else (
                    "бессрочно. (Распространяется только на один пост)"
                    if d.type == PublicationServiceType.HIGHLIGHT
                    else "бессрочно."
                )
            ),
            "price_text": d.price_display,
        }
        for d in active_defs
    ]

    return {
        "services": services,
        "user": user,
    }


@inject
async def getter_connected_services_user(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = dialog_manager.dialog_data["user"]

    publications: list[PublicationDTO] = await mediator.handle(
        GetUserPublicationsRequest(user_id=user.id, region_id=user.region_id)
    )

    cards: list[str] = []
    for pub in publications:
        active_services = [
            svc
            for svc in pub.services
            if svc.status
            in (PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED)
        ]
        if not active_services:
            continue

        service_lines = "\n".join(
            f"  • {svc.type.display} — {svc.price_paid_display}"
            for svc in active_services
        )

        cards.append(
            f"🚘 <b>{pub.plate_number or '—'}</b> ({pub.slot_display})\n"
            f"{service_lines}"
        )

    has_any = len(cards) > 0
    cards_text = "\n\n".join(cards) if has_any else ""

    return {
        "has_any": has_any,
        "cards_text": cards_text,
    }


@inject
async def getter_user_ads_for_service(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    service_type: PublicationServiceType = dialog_manager.start_data["service_type"]
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    publications: list[PublicationDTO] = await mediator.handle(
        GetUserPublicationsRequest(user_id=user.id, region_id=user.region_id)
    )

    seen_ad_ids: set[int] = set()
    eligible = []
    for p in sorted(publications, key=lambda x: x.id):
        if p.status not in (PublicationStatus.PUBLISHED, PublicationStatus.SCHEDULED):
            continue
        if p.ad_id in seen_ad_ids:
            continue

        has_autopublish = any(
            s.type == PublicationServiceType.AUTOPUBLISH
            for s in p.services
        )

        if has_autopublish:
            seen_ad_ids.add(p.ad_id)  # блокируем все дочерние
            continue  # но саму родительскую тоже не показываем

        if any(
            s.type == service_type and s.status in (
                PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED
            )
            for s in p.services
        ):
            seen_ad_ids.add(p.ad_id)
            continue

        if service_type == PublicationServiceType.PRIORITY_PUBLISH and p.status != PublicationStatus.SCHEDULED:
            seen_ad_ids.add(p.ad_id)
            continue

        seen_ad_ids.add(p.ad_id)
        eligible.append(p)

    ads = [
        {
            "id": p.id,
            "title": f"{p.plate_number or '—'} — {p.slot_display}",
        }
        for p in eligible
    ]

    dialog_manager.dialog_data["user"] = user

    return {
        "ads": ads,
        "has_ads": len(ads) > 0,
        "service_name": service_type.display,
    }


@inject
async def getter_buy_service_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    service_type: PublicationServiceType = dialog_manager.start_data["service_type"]
    pub_id: int = dialog_manager.dialog_data["selected_pub_id"]

    definitions: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )
    definition = next((d for d in definitions if d.type == service_type), None)

    pub: PublicationDTO = await mediator.handle(
        GetPublicationByIdRequest(publication_id=pub_id)
    )
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=pub.ad_id))

    return {
        "service_name": definition.title if definition else service_type.value,
        "price_text": definition.price_display if definition else "—",
        "ad_title": f"{ad.content.plate_number} — {pub.slot_display}",
    }


@inject
async def getter_pre_publication_confirm(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    dialog_manager.dialog_data["user"] = user

    definitions: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )
    definition = next(
        (d for d in definitions if d.type == PublicationServiceType.PRE_PUBLICATION),
        None,
    )
    

    now = datetime.now(timezone.utc)
    already_active = (
        user.pre_publication_expires_at is not None
        and user.pre_publication_expires_at > now
    )

    new_expires_at = None
    if already_active and definition:
        new_expires_at = user.pre_publication_expires_at + timedelta(
            days=definition.duration_days or 30
        )
    elif definition:
        new_expires_at = now + timedelta(days=definition.duration_days or 30)

    dialog_manager.dialog_data["definition"] = definition
    dialog_manager.dialog_data["already_active_flag"] = already_active

    return {
        "service_name": definition.title if definition else "",
        "price_text": definition.price_display if definition else "—",
        "duration_text": str(definition.duration_days) if definition and definition.duration_days else "30",
        "already_active": already_active,
        "current_expires_display": (
            user.pre_publication_expires_at.strftime("%d.%m.%Y")
            if already_active else None
        ),
        "new_expires_display": new_expires_at.strftime("%d.%m.%Y") if new_expires_at else None,
    }