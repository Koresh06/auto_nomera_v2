from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.ad import AdDTO
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.domain.enums.publication import PublicationStatus
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.publication.get_user import GetUserPublicationsRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.presentation.telegram.utils.build_media import build_media_attachment


@inject
async def getter_list_publications(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    publications: list[PublicationDTO] = await mediator.handle(
        GetUserPublicationsRequest(
            user_id=user.id,
            region_id=user.region_id,
        )
    )

    dialog_manager.dialog_data["user_id"] = user.id
    dialog_manager.dialog_data["region_id"] = user.region_id

    return {"publications": publications}


@inject
async def getter_detail(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    start_data = dialog_manager.start_data or {}

    pub: PublicationDTO | None = None

    pub_id: int | None = data.get("selected_pub_id") or start_data.get("pub_id")
    ad_id: int | None = start_data.get("ad_id") or data.get("ad_id")

    is_editable = False

    if pub_id:
        pub = await mediator.handle(GetPublicationByIdRequest(publication_id=pub_id))

        ad_id = pub.ad_id

        is_editable = pub.status in (
            PublicationStatus.SCHEDULED,
            PublicationStatus.DRAFT,
            PublicationStatus.CANCELED,
        )
    else:
        is_editable = True

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    dialog_manager.dialog_data["selected_ad_id"] = ad.id
    dialog_manager.dialog_data["ad_id"] = ad_id

    return {
        "pub": pub,
        "can_edit_plate": is_editable,
        "type_ad": ad.ad_type.display,
        "plate": ad.content.plate_number if ad.content else None,
        "city": ad.content.city if ad.content else None,
        "price": ad.content.price.display if ad.content else None,
        "contacts": ad.content.contacts.display if ad.content else None,
        "media": build_media_attachment(
            ad.content.image_file_id if ad.content else None
        ),
    }


async def getter_edit_field(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    start_data = dialog_manager.start_data or {}
    ad_id: int | None = start_data.get("ad_id")
    pub_id: int | None = start_data.get("pub_id")

    dialog_manager.dialog_data["ad_id"] = ad_id
    dialog_manager.dialog_data["pub_id"] = pub_id
    return {
        "edit_label": dialog_manager.dialog_data.get("edit_label", "Введите значение:"),
    }


async def getter_confirm_edit(dialog_manager: DialogManager, **kwargs) -> dict:
    data = dialog_manager.dialog_data
    field = data["edit_field"]
    value = data["pending_value"]

    labels = {
        "city": "🌎 Город",
        "price": "💰 Цена",
        "phone": "📲 Телефон",
        "plate": "🚘 Номер",
    }

    return {
        "field_label": labels.get(field, field),
        "new_value": value,
    }
