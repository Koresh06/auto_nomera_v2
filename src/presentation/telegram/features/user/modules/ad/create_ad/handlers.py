import logging
from datetime import date, time

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.api.entities import MediaAttachment

from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest
from src.application.use_cases.notification.notify_admins_urgent import (
    NotifyAdminsAboutUrgentRequest,
)
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdRequest,
)
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdStatus, AdType
from src.domain.exceptions.slot_reservation import (
    SlotHoldNotFound,
    SlotHoldOwnerMismatch,
)
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.use_cases.ad.find_by_plate import FindAdByPlateRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.reuse_ad_and_schedule import (
    ReuseAdAndScheduleRequest,
)
from src.application.use_cases.slots.check_hold import CheckHoldRequest
from src.application.dtos.user import UpdateUserDTO, UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.publication.create_ad_publication import (
    CreateAndScheduleAdRequest,
)
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest
from src.application.use_cases.user.update import UpdateUserRequest
from src.presentation.telegram.features.user.modules.ad.create_ad.states import (
    CreateAdSG,
)
from src.presentation.telegram.utils.price_validators import (
    validate_price,
    validate_price_urgent_buyout,
)
from src.presentation.telegram.features.user.modules.ad.edit.states import EditAdSG
from src.presentation.telegram.keyboards.urgent_moderation import (
    build_urgent_moderation_kb,
)
from src.presentation.telegram.utils.build_media import build_media_attachment

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
    dialog_manager.dialog_data["is_reuse_ad"] = False

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    if ad_type != AdType.URGENT_BUYOUT:
        existing_ad: AdDTO | None = await mediator.handle(
            FindAdByPlateRequest(
                user_id=user.id,
                region_id=user.region_id,
                plate_number=validated,
            )
        )
        if existing_ad:
            dialog_manager.dialog_data["existing_ad_id"] = existing_ad.id
            dialog_manager.dialog_data["is_reuse_ad"] = True
            await dialog_manager.next()
            return

    await dialog_manager.switch_to(CreateAdSG.image)


async def on_reuse_old_click(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["reuse_ad"] = True
    await dialog_manager.switch_to(CreateAdSG.calendar)


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


async def on_city_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
) -> None:
    dialog_manager.dialog_data["city"] = value
    await dialog_manager.next()


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


async def on_price_input_success(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    value: str,
) -> None:
    ad_type = dialog_manager.dialog_data["ad_type"]
    if ad_type == AdType.URGENT_BUYOUT:
        try:
            validated = validate_price_urgent_buyout(value)
        except ValueError as e:
            await message.answer(str(e))
            return
    else:
        try:
            validated = validate_price(value)
        except ValueError as e:
            await message.answer(str(e))
            return

    dialog_manager.dialog_data["price"] = validated
    if ad_type == AdType.URGENT_BUYOUT:
        await dialog_manager.switch_to(CreateAdSG.confirm)
    else:
        await dialog_manager.next()


@inject
async def on_back_to_calendar(
    callback: CallbackQuery,
    widget: CallbackQuery,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    if "region_id" in data:
        slot: SlotKey = SlotKey(
            region_id=data["region_id"],
            local_day=date.fromisoformat(data["slot_day"]),
            local_time=time.fromisoformat(data["slot_time"]),
        )
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
        data.pop("region_id", None)
        data.pop("slot_day", None)
        data.pop("slot_time", None)


@inject
async def on_confirm_ad(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    tg_id = callback.from_user.id
    data = dialog_manager.dialog_data

    ad_type_raw = data["ad_type"]
    ad_type: AdType = (
        ad_type_raw if isinstance(ad_type_raw, AdType) else AdType(ad_type_raw)
    )

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    region_id: int = data["region_id"]

    plate: str = data["plate"]
    city: str = data["city"]
    price: Price = Price(int(data["price"]))
    phone: str = data["phone"]

    media_file_id = data.get("media_file_id")
    media: MediaAttachment | None = build_media_attachment(media_file_id)

    contacts = Contacts.from_user(username=user.username, phone=phone)

    if ad_type == AdType.URGENT_BUYOUT:
        ad_dto: AdDTO = await mediator.handle(
            CreateAdDraftRequest(
                user_id=user.id,
                region_id=region_id,
                ad_type=AdType.URGENT_BUYOUT,
                status=AdStatus.PENDING_MODERATION,
            )
        )
        await mediator.handle(
            UpdateAdContentRequest(
                ad_id=ad_dto.id,
                plate_number=plate,
                price=price,
                city=city,
                contacts=contacts,
                image_file_id=(
                    media.file_id.file_id if media and media.file_id else None
                ),
            )
        )

        markup = await build_urgent_moderation_kb(ad_id=ad_dto.id)
        await mediator.handle(
            NotifyAdminsAboutUrgentRequest(
                ad_id=ad_dto.id,
                reply_markup=markup,
            )
        )

        data["ad_id"] = ad_dto.id
        logger.info("[on_confirm:urgent] ad_id=%s sent to admins", ad_dto.id)
        await dialog_manager.switch_to(CreateAdSG.urgent_done)
        return

    slot = SlotKey(
        region_id=data["region_id"],
        local_day=date.fromisoformat(data["slot_day"]),
        local_time=time.fromisoformat(data["slot_time"]),
    )

    if data.get("from_existing_draft"):
        ad_id: int = data["ad_id"]

        pub_dto: PublicationDTO = await mediator.handle(
            FinalizeAndScheduleExistingAdRequest(
                ad_id=ad_id,
                slot=slot,
                user_id=user.id,
                payment_confirmed=data.get("is_paid", False),
            )
        )

        data["publication_id"] = pub_dto.id

        logger.info("[on_confirm:from_draft] ad_id=%s pub_id=%s", ad_id, pub_dto.id)
        await dialog_manager.next()
        return

    # обычный путь — холд должен быть жив
    hold_valid: bool = await mediator.handle(
        CheckHoldRequest(
            region_id=region_id,
            slot=slot,
            user_id=user.id,
        )
    )
    if not hold_valid:
        await callback.answer(
            "⏰ Время ожидания подтверждения истекло. Выберите слот заново.",
            show_alert=True,
        )
        await dialog_manager.switch_to(CreateAdSG.calendar)
        return

    if data.get("reuse_ad"):
        ad_id: int = data["existing_ad_id"]
        pub: PublicationDTO = await mediator.handle(
            ReuseAdAndScheduleRequest(
                ad_id=ad_id,
                slot=slot,
                user_id=user.id,
            )
        )
    else:
        pub: PublicationDTO = await mediator.handle(
            CreateAndScheduleAdRequest(
                user_id=user.id,
                region_id=region_id,
                ad_type=ad_type,
                plate=plate,
                city=city,
                price=price,
                contacts=contacts,
                image_file_id=(
                    media.file_id.file_id if media and media.file_id else None
                ),
                slot=slot,
                chat_id=tg_id,
                payment_confirmed=data.get("is_paid", False),
            )
        )

    data["ad_id"] = pub.ad_id
    data["publication_id"] = pub.id

    logger.info("[on_confirm:done] ad created/reused")
    await dialog_manager.next()


@inject
async def on_edit_ad(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    pub_id: int = dialog_manager.dialog_data["publication_id"]

    ad_id = dialog_manager.dialog_data.get("ad_id")
    if ad_id is None:
        pub: PublicationDTO = await mediator.handle(
            GetPublicationByIdRequest(publication_id=pub_id)
        )
        ad_id = pub.ad_id

    await dialog_manager.start(
        state=EditAdSG.detail,
        data={
            "ad_id": ad_id,
            "pub_id": pub_id,
            "back_to_finish": True,
        },
    )


