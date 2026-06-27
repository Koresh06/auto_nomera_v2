from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Select, Button
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.api.entities import MediaAttachment
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application import mediator
from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.archive_ad import ArchiveAdRequest
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest

from src.application.use_cases.publication.edit_published import EditPublishedAdRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.get_user import GetUserPublicationsRequest
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.user.get_by_tg_id import (
    GetByTgIdUserUseCase,
    GetTgIdRequest,
)
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.enums.publication import PublicationStatus
from src.presentation.telegram.features.user.modules.ad.create_ad.texts import (
    PLATE_BUY_EDIT_TEXT,
    PLATE_SALE_EDIT_TEXT,
)
from src.presentation.telegram.features.user.modules.ad.create_ad.validators import (
    validate_phone_number,
    validate_price,
)
from .states import EditAdSG


@inject
async def on_select_publication(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    publications: list[PublicationDTO] = await mediator.handle(
        GetUserPublicationsRequest(
            user_id=data["user_id"],
            region_id=data["region_id"],
        )
    )
    pub: PublicationDTO | None = next(
        (p for p in publications if str(p.id) == item_id), None
    )
    if pub is None:
        return

    dialog_manager.dialog_data["selected_pub_id"] = pub.id
    dialog_manager.dialog_data["pub_id"] = pub.id
    dialog_manager.dialog_data["ad_id"] = pub.ad_id
    await dialog_manager.next()


@inject
async def on_delete_ad(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    if dialog_manager.dialog_data.get("delete_warning"):
        dialog_manager.dialog_data.pop("delete_warning", None)
        ad_id = dialog_manager.dialog_data["ad_id"]
        pub_id = dialog_manager.dialog_data.get("pub_id")
        await mediator.handle(
            ArchiveAdRequest(
                ad_id=ad_id,
                publication_id=pub_id,
            )
        )
        await callback.answer("🗑 Объявление удалено.", show_alert=False)
        await dialog_manager.back()
    else:
        dialog_manager.dialog_data["delete_warning"] = True
        await callback.answer(
            "⚠️ Вы уверены? Нажмите ещё раз для подтверждения.",
            show_alert=True,
        )


async def on_edit_city(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
):
    dialog_manager.dialog_data["edit_field"] = "city"
    dialog_manager.dialog_data["edit_label"] = "🌎 Введите новый город:"
    await dialog_manager.switch_to(EditAdSG.edit_field)


async def on_edit_price(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
):
    dialog_manager.dialog_data["edit_field"] = "price"
    dialog_manager.dialog_data["edit_label"] = (
        "💰 <b>Укажите новую стоимость номера, за которую хотите продать.</b>\n\n"
        "📌 <b>Примеры:</b>\n\n"
        "➡️ <code>0</code> - <b>договорная</b>\n"
        "➡️ <code>1000</code>\n"
        "➡️ <code>100000</code>\n"
        "➡️ <code>1000000</code>"
    )

    await dialog_manager.switch_to(EditAdSG.edit_field)


async def on_edit_phone(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
):
    dialog_manager.dialog_data["edit_field"] = "phone"
    dialog_manager.dialog_data["edit_label"] = (
        "📞 <b>Укажите новый номер телефона (с 8 или +7, без пробелов и лишних символов):</b>"
    )
    await dialog_manager.switch_to(EditAdSG.edit_field)


@inject
async def on_edit_plate(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
):
    ad_id: int = dialog_manager.dialog_data.get("selected_ad_id") or dialog_manager.dialog_data.get("ad_id")
    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))

    pub_id: int | None = dialog_manager.dialog_data.get("selected_pub_id") or dialog_manager.dialog_data.get("pub_id")
    if pub_id:
        pub: PublicationDTO = await mediator.handle(
            GetPublicationByIdRequest(publication_id=pub_id)
        )
        if pub.status == PublicationStatus.PUBLISHED:
            await callback.answer(
                "⚠️ Номер уже опубликован — изменить его нельзя.",
                show_alert=True,
            )
            return

    if ad.ad_type == AdType.BUY:
        dialog_manager.dialog_data["edit_label"] = PLATE_BUY_EDIT_TEXT
    else:
        dialog_manager.dialog_data["edit_label"] = PLATE_SALE_EDIT_TEXT
    dialog_manager.dialog_data["edit_field"] = "plate"
    await dialog_manager.switch_to(EditAdSG.edit_field)


@inject
async def on_field_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    field = data["edit_field"]
    ad_id: int = data["selected_ad_id"] or data["ad_id"]

    ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=message.from_user.id)
    )

    c = ad.content

    current_value = {
        "city": c.city if c else "",
        "price": str(c.price.value) if c else "0",
        "phone": c.contacts.phone if c and c.contacts else "",
        "plate": c.plate_number if c else "",
    }.get(field, "")

    if value.strip() == str(current_value).strip():
        await message.answer("⚠️ Вы ввели то же самое значение. Измените данные.")
        return

    try:
        if field == "plate":
            value = validate_plate(value, allow_mask=False)
            region: RegionDTO = await mediator.handle(
                IdRegionRequest(user.region_id)
            )
            new_media: MediaAttachment = await mediator.handle(
                EnsureAdImageRefRequest(
                    plate=value,
                    channel_username=region.channel_username,
                    chat_id=message.from_user.id,
                )
            )
            data["pending_media_file_id"] = new_media.file_id.file_id if new_media.file_id else None
            
        elif field == "price":
            validate_price(value)
        elif field == "phone":
            value = validate_phone_number(value)
    except ValueError as e:
        await message.answer(str(e))
        return

    plate = value if field == "plate" else None
    city = value if field == "city" else None
    price = Price(int(value)) if field == "price" else None
    contacts = (
        Contacts.from_user(username=user.username, phone=value)
        if field == "phone"
        else None
    )

    data["pending_value"] = value
    data["pending_plate"] = plate
    data["pending_city"] = city
    data["pending_price"] = price.value if price else None
    data["pending_contacts"] = contacts.display if contacts else None

    await dialog_manager.switch_to(EditAdSG.confirm_edit)


@inject
async def on_apply_edit(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data["ad_id"]
    pub_id: int | None = data.get("selected_pub_id") or data.get("pub_id")
    plate = data.get("pending_plate")
    city = data.get("pending_city")
    price_raw: int | None = data.get("pending_price")
    price: Price | None = Price(price_raw) if price_raw is not None else None
    contacts: Contacts | None = data.get("pending_contacts")

    if pub_id is not None:
        pub: PublicationDTO = await mediator.handle(
            GetPublicationByIdRequest(publication_id=pub_id)
        )
    
        if pub.status == PublicationStatus.PUBLISHED:
            await mediator.handle(
                EditPublishedAdRequest(
                    ad_id=ad_id,
                    publication_id=pub.id,
                    city=city,
                    price=price,
                    contacts=contacts, 
                )
            )
        else:
            file_id_media = data.get("pending_media_file_id")
            await mediator.handle(
                UpdateAdContentRequest(
                    ad_id=ad_id,
                    plate_number=plate,
                    city=city,
                    price=price,
                    contacts=contacts,
                    image_file_id=file_id_media,
                )
            )

    updated_ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=ad_id))
    data["selected_ad_id"] = updated_ad.id

    await dialog_manager.switch_to(EditAdSG.detail)
