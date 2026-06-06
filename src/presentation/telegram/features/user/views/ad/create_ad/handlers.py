import logging

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from aiogram_dialog.widgets.kbd import Select, Button
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.api.entities import MediaAttachment

from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka

from src.application.use_cases.publication.create_ad_publication import CreateAndScheduleAdRequest
from src.domain.enums.ad import AdStatus, AdType
from src.domain.exceptions.slot_reservation import SlotAlreadyBooked, SlotAlreadyConverted, SlotAlreadyHeld, SlotHoldNotFound, SlotHoldOwnerMismatch
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.services.slots.slot_reservation_service import HoldResult
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.user import UpdateUserDTO, UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator

from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest
from src.application.use_cases.ad.finalize_ad import FinalizeAdRequest
from src.application.use_cases.publication.create_publication_from_ad import CreatePublicationFromAdRequest

from src.application.use_cases.publication.select_slot_for_publication import SelectSlotForPublicationRequest
from src.application.use_cases.slots.hold_slot import HoldSlotRequest
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest
from src.application.use_cases.user.update import UpdateUserRequest


logger = logging.getLogger(__name__)


@inject
async def on_plate_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    ad_type = dialog_manager.dialog_data["ad_type"]
    allow_mask = ad_type == AdType.BUY

    try:
        validated = validate_plate(value, allow_mask=allow_mask)
    except ValueError as e:
        await message.answer(str(e))
        return

    dialog_manager.dialog_data["plate"] = validated
    await dialog_manager.next()


async def on_input_photo(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["photo"] = {
        "file_id": message.photo[-1].file_id,  # type: ignore
        "file_unique_id": message.photo[-1].file_unique_id,  # type: ignore
    }


async def on_delete_photo(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    if "photo" in dialog_manager.dialog_data:
        dialog_manager.dialog_data.pop("photo")
        await callback.answer("Фото удалено. Отправьте новое.")
    else:
        await callback.answer("Фото для удаления не найдено.", show_alert=True)


async def on_negotiable_price(
    callbck: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["price"] = 0
    await dialog_manager.next()


@inject
async def on_phone_received_contact(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
):
    new_phone = message.contact.phone_number
    if not new_phone.startswith("+"):
        new_phone = f"+{new_phone}"

    dialog_manager.dialog_data["phone"] = new_phone
    old_phone = dialog_manager.dialog_data.get("current_phone")

    if new_phone and new_phone != old_phone:
        try:
            await mediator.handle(
                UpdateUserRequest(
                    tg_id=message.from_user.id,
                    data=UpdateUserDTO(phone=new_phone),
                )
            )
        except UserNotFoundException as ex:
            logger.info(str(ex))
            await message.answer("Пользователь не найден")

    await dialog_manager.next()


@inject
async def on_phone_input_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
):
    new_phone = value.strip()
    dialog_manager.dialog_data["phone"] = new_phone
    old_phone = dialog_manager.dialog_data.get("current_phone")

    if new_phone and new_phone != old_phone:
        try:
            await mediator.handle(
                UpdateUserRequest(
                    tg_id=message.from_user.id,
                    data=UpdateUserDTO(phone=new_phone),
                )
            )
        except UserNotFoundException as ex:
            logger.info(str(ex))
            await message.answer("Пользователь не найден")

    await dialog_manager.next()


@inject
async def on_pick_slot(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    user: UserDTO = dialog_manager.dialog_data["user"]
    slot: SlotKey = SlotKey.decode_slot_id(item_id, user.region_id)

    try:
        result: HoldResult = await mediator.handle(
            HoldSlotRequest(
                region_id=user.region_id,
                slot=slot,
                user_id=user.id,
            )
        )
    except (SlotAlreadyHeld, SlotAlreadyConverted):
        if dialog_manager.dialog_data.get("held_warning") == item_id:
            dialog_manager.dialog_data["slot_id"] = item_id
            dialog_manager.dialog_data["slot_day"] = slot.date_display
            dialog_manager.dialog_data["slot_time"] = slot.time_display
            dialog_manager.dialog_data["is_paid"] = True
            dialog_manager.dialog_data.pop("held_warning", None)
            # await dialog_manager.next()
            await callback.answer("💰 Опата слота", show_alert=True)
        else:
            dialog_manager.dialog_data["held_warning"] = item_id
            await callback.answer(
                "💰 Этот слот платный. Нажмите ещё раз для продолжения к оплате.",
                show_alert=True,
            )
        return

    dialog_manager.dialog_data["slot_id"] = item_id
    dialog_manager.dialog_data["slot"] = slot
    dialog_manager.dialog_data["is_paid"] = result.pricing_changed_to_converted

    await dialog_manager.next()


@inject
async def on_back_to_calendar(
    callback: CallbackQuery,
    widget: CallbackQuery,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    user: UserDTO = data["user"]

    if "slot_id" in data:
        slot: SlotKey = SlotKey.decode_slot_id(data["slot_id"], user.region_id)
        try:
            await mediator.handle(
                ReleaseHoldRequest(
                    slot=slot,
                    user_id=user.id,
                )
            )
            logger.info("[ReleaseHold:done] slot released")
        except (SlotHoldNotFound, SlotHoldOwnerMismatch) as e:
            logger.info(str(e))
        data.pop("slot_id", None)


@inject
async def on_confirm(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    tg_id = callback.from_user.id
    data = dialog_manager.dialog_data

    user: UserDTO = data["user"]
    region_id: int = data["region_id"]
    ad_type: AdType = data["ad_type"]
    plate: str = data["plate"]
    city: str = data["city"]
    price: Price = Price(int(data["price"]))
    phone: str = data["phone"]
    media: MediaAttachment = data["media"]
    slot: SlotKey = data["slot"]
    contacts = Contacts.from_user(username=user.username, phone=phone)

    await mediator.handle(
        CreateAndScheduleAdRequest(
            user_id=user.id,
            region_id=region_id,
            ad_type=ad_type,
            plate=plate,
            city=city,
            price=price,
            contacts=contacts,
            image_file_id=media.file_id.file_id if media else None,
            slot=slot,
            chat_id=tg_id,
        )
    )
    logger.info("[CreateAndScheduleAd:done] ad created")
    await dialog_manager.next()