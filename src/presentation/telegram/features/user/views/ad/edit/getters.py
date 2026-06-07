from aiogram_dialog import DialogManager
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.ad import AdDTO
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
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
    pub: PublicationDTO = data["selected_pub"]
    pub_status = pub.status not in (
        PublicationStatus.PUBLISHED,
        PublicationStatus.CANCELED,
        PublicationStatus.REPLACED,
    )
    ad_id: int = pub.ad_id
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    dialog_manager.dialog_data["selected_ad"] = ad
    
    return {
        "pub": pub,
        "pub_status": pub_status,
        "type_ad": ad.ad_type.display,
        "plate": ad.content.plate_number if ad.content else None,
        "city": ad.content.city if ad.content else None,
        "price": ad.content.price.display if ad.content else None,
        "contacts": ad.content.contacts.display if ad.content else None,
        "media": build_media_attachment(ad.content.image_file_id if ad.content else None),
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