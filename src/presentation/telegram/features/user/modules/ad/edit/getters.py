from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.ad import AdDTO
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.domain.enums.publication import PublicationStatus
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.ports.publication.get_user import GetUserPublicationsRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.presentation.telegram.utils import build_media_attachment


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
    dialog_manager.dialog_data["user"] = user
    dialog_manager.dialog_data["publications"] = publications
    return {"publications": publications}


@inject
async def getter_detail(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    data = dialog_manager.dialog_data
    start_data = dialog_manager.start_data or {}

    pub: PublicationDTO | None = data.get("selected_pub")
    pub_status = False
    # back_to_finish: bool | None = start_data.get("back_to_finish")

    if pub is None:
        pub_id: int | None = start_data.get("pub_id")
        ad_id: int | None  = start_data.get("ad_id") or data.get("ad_id")

        if pub_id:
            pub: PublicationDTO = await mediator.handle(
                GetPublicationByIdRequest(publication_id=pub_id)
            )
            pub_status = pub.status not in (
                PublicationStatus.PUBLISHED,
                PublicationStatus.CANCELED,
                PublicationStatus.REPLACED,
            )
    else:
        ad_id = pub.ad_id
        pub_status = pub.status not in (
            PublicationStatus.PUBLISHED,
            PublicationStatus.CANCELED,
            PublicationStatus.REPLACED,
        )

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    dialog_manager.dialog_data["selected_ad"] = ad
    dialog_manager.dialog_data["ad_id"] = ad_id

    return {
        "pub": pub,
        "pub_status": pub_status,
        "type_ad": ad.ad_type.display,
        "plate": ad.content.plate_number if ad.content else None,
        "city": ad.content.city if ad.content else None,
        "price": ad.content.price.display if ad.content else None,
        "contacts": ad.content.contacts.display if ad.content else None,
        "media": build_media_attachment(ad.content.image_file_id if ad.content else None),
        # "back_to_finish": back_to_finish,
    }


async def getter_edit_field(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
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