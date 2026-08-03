from datetime import datetime, timedelta, timezone

from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram_dialog import DialogManager

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.publication_service import PublicationServiceDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_all_user_publications import (
    GetAllUserPublicationsRequest,
)
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.get_user import GetUserPublicationsRequest
from src.application.use_cases.publication_service.get_ad_ids_with_active_autipublish_series import (
    GetAdIdsWithActiveAutopublishSeriesRequest,
)
from src.application.use_cases.service_difinition.get_all import GetAllServicesRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
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
    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["region_id"] = user.region_id

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
                    or d.type == PublicationServiceType.PRIORITY_PUBLISH
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
    user_id: int = dialog_manager.dialog_data["user_id"]
    region_id: int = dialog_manager.dialog_data["region_id"]

    publications: list[PublicationDTO] = await mediator.handle(
        GetAllUserPublicationsRequest(user_id=user_id, region_id=region_id)
    )

    by_ad: dict[int, list[PublicationDTO]] = {}
    for pub in publications:
        by_ad.setdefault(pub.ad_id, []).append(pub)

    cards: list[str] = []
    for ad_id, pubs in by_ad.items():
        all_services = [
            svc
            for pub in pubs
            for svc in pub.services
            if svc.status
            in (PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED)
        ]
        if not all_services:
            continue

        # заголовок и слот берём с самой свежей публикации семьи
        all_services.sort(key=lambda s: s.created_at)
        latest = max(
            pubs,
            key=lambda p: p.publish_at_utc or datetime.min.replace(tzinfo=timezone.utc),
        )

        service_lines = "\n".join(
            f"  • {svc.type.display} — {svc.price_paid_display} ({svc.created_at_display})"
            for svc in all_services
        )
        cards.append(
            f"<b>{latest.display_title}</b> ({latest.slot_display})\n{service_lines}"
        )

    has_any = len(cards) > 0
    cards_text = "\n\n".join(cards) if has_any else ""

    return {
        "has_any": has_any,
        "cards_text": cards_text,
    }


REPEATABLE_ALWAYS = {PublicationServiceType.PRIORITY_PUBLISH}


def _is_blocking(
    s: PublicationServiceDTO,
    service_type: PublicationServiceType,
) -> bool:
    if s.type != service_type:
        return False

    if s.status == PublicationServiceStatus.ACTIVE:
        return True

    if s.status != PublicationServiceStatus.USED:
        return False

    if service_type in REPEATABLE_ALWAYS:
        return False

    if service_type == PublicationServiceType.PIN:
        unpin_at_raw = s.params.get("unpin_at_utc") if s.params else None
        if not unpin_at_raw:
            return True
        return datetime.fromisoformat(unpin_at_raw) > datetime.now(timezone.utc)

    return True


@inject
async def getter_user_ads_for_service(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    service_type_raw = dialog_manager.start_data["service_type"]
    service_type: PublicationServiceType = PublicationServiceType(service_type_raw)
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))

    publications: list[PublicationDTO] = await mediator.handle(
        GetUserPublicationsRequest(user_id=user.id, region_id=region.id)
    )

    blocked_ad_ids: set[int] = set()
    if service_type == PublicationServiceType.AUTOPUBLISH:
        ad_ids = [p.ad_id for p in publications]
        blocked_ad_ids = await mediator.handle(
            GetAdIdsWithActiveAutopublishSeriesRequest(ad_ids=ad_ids)
        )

    eligible: list[PublicationDTO] = []
    for p in publications:
        if p.status not in (PublicationStatus.PUBLISHED, PublicationStatus.SCHEDULED):
            continue
        if service_type == PublicationServiceType.HIGHLIGHT and p.shop_name:
            continue
        if any(_is_blocking(s, service_type) for s in p.services):
            continue
        if p.ad_id in blocked_ad_ids:
            continue
        eligible.append(p)

    ads = [{"id": p.id, "title": p.display_title} for p in eligible]

    dialog_manager.dialog_data["user_id"] = user.id

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

    dialog_manager.dialog_data["definition_id"] = definition.id

    return {
        "service_name": definition.title if definition else service_type.value,
        "price_text": definition.price_display if definition else "—",
        "ad_title": (ad.content.plate_number if ad.content else None)
        or (ad.store_content.shop_name if ad.store_content else None)
        or "—",
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

    definitions: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )
    definition = next(
        (d for d in definitions if d.type == PublicationServiceType.PRE_PUBLICATION)
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

    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["definition_id"] = definition.id
    dialog_manager.dialog_data["already_active_flag"] = already_active

    return {
        "service_name": definition.title if definition else "",
        "description": definition.description if definition else "",
        "duration_text": (
            str(definition.duration_days)
            if definition and definition.duration_days
            else "30"
        ),
        "price_text": definition.price_display if definition else "—",
        "already_active": already_active,
        "current_expires_display": (
            user.pre_publication_expires_at.strftime("%d.%m.%Y")
            if already_active
            else None
        ),
        "new_expires_display": (
            new_expires_at.strftime("%d.%m.%Y") if new_expires_at else None
        ),
    }
