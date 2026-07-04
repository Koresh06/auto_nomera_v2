from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.user import UserDTO
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_id import GetByIdRequest
from src.core.config import settings
from src.application.dtos.catalog_card import CatalogCardDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.schedule_stats import RegionScheduleDTO
from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    CatalogItem,
)
from src.application.use_cases.publication.get_admin_scheduled_catalog import (
    GetAdminScheduledCatalogRequest,
)
from src.application.use_cases.region.get_all import GetRegionsRequest
from src.application.use_cases.stats.region_schedule import GetRegionScheduleRequest
from src.domain.enums.ad import AdType
from src.domain.enums.period import StatsPeriod
from src.application.dtos.publication_stats import PublicationStatsDTO
from src.application.mediator import Mediator
from src.application.use_cases.stats.publication import GetPublicationStatsRequest
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.presentation.telegram.features.admin.modules.stats.helper import period_flags
from src.presentation.telegram.utils.build_media import build_media_attachment


def _current_period(dm: DialogManager) -> StatsPeriod:
    return StatsPeriod(dm.dialog_data.get("period", StatsPeriod.MONTH.value))


@inject
async def getter_pub_stats(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    period = _current_period(dialog_manager)
    stats: PublicationStatsDTO = await mediator.handle(
        GetPublicationStatsRequest(period=period)
    )

    status_lines = (
        "\n".join(
            f"  {s.label}: <b>{s.count}</b>"
            for s in sorted(stats.by_status, key=lambda x: x.count, reverse=True)
        )
        or "  —"
    )

    type_lines = (
        "\n".join(
            f"  {t.label}: <b>{t.count}</b>"
            for t in sorted(stats.by_ad_type, key=lambda x: x.count, reverse=True)
        )
        or "  —"
    )

    top_region = (
        f"{stats.top_region_title} ({stats.top_region_count})"
        if stats.top_region_title
        else "—"
    )

    return {
        "period_label": period.label(),
        "total": stats.total,
        "status_lines": status_lines,
        "type_lines": type_lines,
        "top_region": top_region,
        **period_flags(period),
    }


@inject
async def getter_schedule_regions(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    regions: list[RegionDTO] = await mediator.handle(GetRegionsRequest())
    return {"regions": regions, "has_regions": bool(regions)}


@inject
async def getter_region_schedule(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.dialog_data["region_id"]
    schedule: RegionScheduleDTO = await mediator.handle(
        GetRegionScheduleRequest(region_id=region_id)
    )

    legend = (
        "🔴 Продажа | 🟢 Покупка | ⚡ Срочно | 🏪 Магазин\n"
        "✅ Опубликовано | 🕓 В ожидании | 📤 Публикуется"
    )

    blocks = []
    for day in schedule.days:
        header = f"📅 <b>{day.date}</b> ({day.count} пост.)"
        if day.slots:
            lines = "\n".join(
                f"  {s.time} | <code>{s.plate}</code> | {s.type_emoji} | {s.status_emoji} {s.owner_link}        "
                for s in day.slots
            )
        else:
            lines = "  — пусто"
        blocks.append(f"{header}\n{lines}")

    schedule_text = "\n\n".join(blocks)
    has_any = any(day.slots for day in schedule.days)

    return {
        "region_title": schedule.region_title,
        "legend": legend,
        "schedule_text": schedule_text,
        "has_any": has_any,
    }


@inject
async def getter_admin_catalog(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.dialog_data["region_id"]

    region_dto: RegionDTO = await mediator.handle(IdRegionRequest(region_id))
    region = region_dto.to_entity()

    items: list[CatalogItem] = await mediator.handle(
        GetAdminScheduledCatalogRequest(region_id=region_id)
    )

    has_ads = len(items) > 0
    dialog_manager.dialog_data["count_page"] = len(items)

    current_page = 0
    scroll = dialog_manager.find("catalog_scroll")
    if scroll:
        current_page = await scroll.get_page()
    current_page = max(0, min(current_page, len(items) - 1)) if has_ads else 0

    card: CatalogCardDTO | None = None
    current_media = None

    if has_ads:
        item = items[current_page]
        ad = item.ad
        pub = item.publication

        owner: UserDTO = await mediator.handle(GetByIdRequest(user_id=ad.user_id))
        owner_tg_id = owner.tg_id

        dialog_manager.dialog_data["current_pub_id"] = pub.id
        dialog_manager.dialog_data["current_user_id"] = ad.user_id

        pub_time = None
        if pub and pub.slot:
            pub_time = f"{pub.slot.date_display} в {pub.slot.time_display}"

        renderer = AdTextRenderer(
            bot_url=settings.telegram.bot_url,
            buyout_url=settings.telegram.buyout_url,
        )
        ad_text = renderer.render(ad=ad, region=region)

        if ad.content and ad.content.contacts.username:
            user_link = f"@{ad.content.contacts.username}"
        elif ad.store_content and ad.store_content.contacts.username:
            user_link = f"@{ad.store_content.contacts.username}"
        else:
            user_link = f'<a href="tg://user?id={owner_tg_id}">👤 Профиль</a>'

        if pub is not None:
            services_line = pub.services_display
        else:
            services_line = "—"

        if ad.ad_type == AdType.STORE and ad.store_content:
            sc = ad.store_content
            dialog_manager.dialog_data["current_label"] = f"магазина «{sc.shop_name}»"
            card = CatalogCardDTO(
                plate=sc.shop_name,
                city=sc.city,
                price="",
                contacts=sc.contacts.display,
                image_file_id=None,
                is_urgent=False,
                pub_time=pub_time,
                ad_type_display=ad.ad_type.display,
                ad_text=ad_text,
                owner_tg_id=owner_tg_id,
                owner_link=user_link,
                services_line=services_line,
            )
        elif ad.content:
            c = ad.content
            dialog_manager.dialog_data["current_label"] = f"номера {c.plate_number}"
            card = CatalogCardDTO(
                plate=c.plate_number or "",
                city=c.city,
                price=c.price.display,
                contacts=c.contacts.display,
                image_file_id=c.image_file_id,
                is_urgent=False,
                pub_time=pub_time,
                ad_type_display=ad.ad_type.display,
                ad_text=ad_text,
                owner_tg_id=owner_tg_id,
                owner_link=user_link,
                services_line=services_line,
            )
            current_media = build_media_attachment(c.image_file_id)

    return {
        "has_ads": has_ads,
        "count_page": len(items),
        "current_page_display": current_page + 1,
        "current_media": current_media,
        "card": card,
    }


@inject
async def getter_admin_catalog_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    region_id: int = dialog_manager.dialog_data["region_id"]
    scroll = dialog_manager.find("catalog_scroll")
    current_page = await scroll.get_page() if scroll else 0

    items: list[CatalogItem] = await mediator.handle(
        GetAdminScheduledCatalogRequest(region_id=region_id)
    )

    buttons = []
    for idx, item in enumerate(items):
        ad = item.ad
        prefix = "👉 " if idx == current_page else ""
        if ad.ad_type == AdType.STORE and ad.store_content:
            buttons.append(
                (
                    f"{prefix}🏦 {ad.store_content.shop_name} • {len(ad.store_content.items)} шт.",
                    str(idx),
                )
            )
        elif ad.content:
            c = ad.content
            buttons.append(
                (
                    f"{prefix}🕐 {c.plate_number} • {ad.ad_type.display} • {c.price.display}",
                    str(idx),
                )
            )

    return {"catalog_buttons": buttons, "has_ads": len(buttons) > 0}
