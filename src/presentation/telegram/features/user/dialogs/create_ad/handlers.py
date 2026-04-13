import logging
from datetime import date, time

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from aiogram_dialog.widgets.kbd import Select, Button

from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator

from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest
from src.application.use_cases.ad.finalize_ad import FinalizeAdRequest
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
)

from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
)

from src.application.use_cases.user.update import UpdateUserRequest
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.value_objects.slot_key import SlotKey

from .states import CreateAdSG


logger = logging.getLogger(__name__)


REGION_ID_DEV = 1


async def on_input_error(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(str(error))


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
    

# @inject
# async def on_contacts_success(
#     message: Message,
#     widget: ManagedTextInput,
#     dialog_manager: DialogManager,
#     value: str,
#     mediator: FromDishka[Mediator],
# ) -> None:
#     ad_id = dialog_manager.dialog_data["ad_id"]
#     await mediator.handle(UpdateAdContentRequest(ad_id=ad_id, contacts=value))

#     # финализация (если фото нет — проставит my://... для генератора)
#     await mediator.handle(FinalizeAdRequest(ad_id=ad_id, chat_id=message.chat.id))

#     # создаём publication
#     pub: PublicationDTO = await mediator.handle(
#         CreatePublicationFromAdRequest(ad_id=ad_id)
#     )
#     dialog_manager.dialog_data["publication_id"] = pub.id

#     await dialog_manager.switch_to(CreateAdSG.calendar)

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
                    data=UpdateUserDTO(
                        phone=new_phone
                    )
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
                    data=UpdateUserDTO(
                        phone=new_phone
                    )
                )
            )
        except UserNotFoundException as ex:
            logger.info(str(ex))
            await message.answer("Пользователь не найден")

    await dialog_manager.next()


def _decode_slot_id(slot_id: str) -> tuple[date, time]:
    # ожидаем формат: YYYY_MM_DD_HH_MM
    y, m, d, hh, mm = map(int, slot_id.split("_"))
    return date(y, m, d), time(hh, mm)


@inject
async def on_pick_slot(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    pub_id = dialog_manager.dialog_data["publication_id"]
    ad_id = dialog_manager.dialog_data["ad_id"]

    day, t = _decode_slot_id(item_id)
    slot = SlotKey(region_id=REGION_ID_DEV, local_day=day, local_time=t)

    res = await mediator.handle(
        SelectSlotForPublicationRequest(
            publication_id=pub_id,
            slot=slot,
            user_id=callback.from_user.id,
            ad_id=ad_id,
        )
    )

    dialog_manager.dialog_data["picked"] = item_id
    dialog_manager.dialog_data["converted"] = getattr(
        res, "pricing_changed_to_converted", False
    )

    await dialog_manager.switch_to(CreateAdSG.done)
