from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.region import RegionDTO
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.core.config import settings
from src.application.dtos.catalog_card import CatalogCardDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.catalog.get_catalog_deferred_publications import CatalogItem, GetCatalogDeferredPublicationsRequest
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.presentation.telegram.utils.build_media import build_media_attachment


@inject
async def getter_urgent_catalog(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    tg_id = dialog_manager.event.from_user.id
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    dialog_manager.dialog_data["region_id"] = user.region_id


    region_dto: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))
    region = region_dto.to_entity()

    items: list[CatalogItem] = await mediator.handle(
        GetCatalogDeferredPublicationsRequest(region_id=user.region_id)
    )

    has_ads = len(items) > 0
    dialog_manager.dialog_data["count_page"] = len(items)

    current_page = 0
    scroll = dialog_manager.find("catalog_scroll")
    if scroll:
        current_page = await scroll.get_page()
    current_page = max(0, min(current_page, len(items) - 1))

    card: CatalogCardDTO | None = None
    current_media = None
    if has_ads:
        item = items[current_page]
        ad = item.ad
        c = ad.content

        renderer = AdTextRenderer(
            bot_url=settings.telegram.bot_url,
            buyout_url=settings.telegram.buyout_url,
        )
        ad_text = renderer.render(ad=ad, region=region)

        pub_time = None
        if item.publication and item.publication.slot:
            slot = item.publication.slot
            pub_time = f"{slot.date_display} в {slot.time_display}"

        card = CatalogCardDTO(
            plate=c.plate_number if c else "",
            city=c.city if c else "",
            price=c.price.display if c else "",
            contacts=c.contacts.display if c else "",
            image_file_id=c.image_file_id if c else None,
            is_urgent=item.is_urgent,
            pub_time=pub_time,
            ad_type_display=ad.ad_type.display,
            ad_text=ad_text,
        )
        current_media = build_media_attachment(c.image_file_id if c else None)

    return {
        "has_ads": has_ads,
        "count_page": len(items),
        "current_page_display": current_page + 1,
        "current_media": current_media,
        "card": card,
        "is_admin": tg_id in settings.telegram.admin_ids,
    }


@inject
async def getter_catalog_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.dialog_data["region_id"]
    current_page = dialog_manager.dialog_data.get("count_page", 0)
    
    scroll = dialog_manager.find("catalog_scroll")
    current_page = await scroll.get_page() if scroll else 0

    items: list[CatalogItem] = await mediator.handle(
        GetCatalogDeferredPublicationsRequest(region_id=region_id)
    )

    buttons = [
        (
            f"{'👉 ' if idx == current_page else ''}"
            f"{'🚨' if item.is_urgent else '🕐'} "
            f"{item.ad.content.plate_number} • "
            f"{item.ad.ad_type.display} • "
            f"{item.ad.content.price.display}",
            str(idx),
        )
        for idx, item in enumerate(items)
        if item.ad.content
    ]

    return {
        "catalog_buttons": buttons,
        "has_ads": len(buttons) > 0,
    }