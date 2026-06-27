from datetime import date, time
from decimal import Decimal
import logging

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import BgManagerFactory, DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from aiogram_dialog.widgets.kbd import Select, Button
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.api.entities import MediaAttachment

from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.ports.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceRequest,
)
from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest
from src.application.use_cases.notification.notify_admins_urgent import (
    NotifyAdminsAboutUrgentRequest,
)
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdRequest,
)
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.payment import PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.exceptions.slot_reservation import (
    SlotAlreadyConverted,
    SlotAlreadyHeld,
    SlotHoldNotFound,
    SlotHoldOwnerMismatch,
)
from src.domain.exceptions.user import InsufficientBalance
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.services.publication.limiter import LimitCheckResult
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.slot_reservation_service import HoldResult
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.region import RegionDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.use_cases.ad.find_by_plate import FindAdByPlateRequest
from src.application.use_cases.publication.check_limiter import (
    CheckPublicationLimitRequest,
)
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.reuse_ad_and_schedule import (
    ReuseAdAndScheduleRequest,
)
from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedRequest,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
)
from src.application.use_cases.publication_service.get_all import GetAllServicesRequest
from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationRequest,
)
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.use_cases.slots.check_hold import CheckHoldRequest
from src.application.dtos.user import UpdateUserDTO, UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.publication.create_ad_publication import (
    CreateAndScheduleAdRequest,
)
from src.application.use_cases.slots.hold_slot import HoldSlotRequest
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest
from src.application.use_cases.user.update import UpdateUserRequest
from src.presentation.telegram.features.user.modules.ad.create_ad.states import (
    CreateAdSG,
)
from src.presentation.telegram.features.user.modules.ad.create_ad.validators import (
    validate_price,
    validate_price_urgent_buyout,
)
from src.presentation.telegram.features.user.modules.ad.edit.states import EditAdSG
from src.presentation.telegram.features.user.modules.payment.helpers import (
    PaymentStartParams,
    start_payment,
)
from src.presentation.telegram.features.user.modules.payment.states import PaymentSG
from src.presentation.telegram.keyboards.urgent_moderation import (
    build_urgent_moderation_kb,
)
from src.presentation.telegram.utils import build_media_attachment

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
async def on_pick_slot(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )
    slot: SlotKey = SlotKey.decode_slot_id(item_id, user.region_id)
    ad_type: AdType = dialog_manager.dialog_data["ad_type"]
    plate: str = dialog_manager.dialog_data["plate"]

    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))
    publish_at_utc = PublishTimeResolver().resolve_publish_at_utc(
        tz=region.timezone, slot=slot
    )

    limit_result: LimitCheckResult = await mediator.handle(
        CheckPublicationLimitRequest(
            user_id=user.id,
            region_id=user.region_id,
            ad_type=ad_type,
            plate=plate,
            publish_at_utc=publish_at_utc,
            region_timezone=region.timezone.value,
        )
    )
    if not limit_result.allowed:
        await callback.answer(limit_result.reason, show_alert=True)
        return

    try:
        result: HoldResult = await mediator.handle(
            HoldSlotRequest(
                region_id=user.region_id,
                slot=slot,
                user_id=user.id,
            )
        )
        logger.info(
            f"[on_pick_slot] pricing_changed_to_converted={result.pricing_changed_to_converted}"
        )
    except (SlotAlreadyHeld, SlotAlreadyConverted):
        if dialog_manager.dialog_data.get("held_warning") == item_id:
            dialog_manager.dialog_data.pop("held_warning", None)
            await _start_slot_payment(
                dialog_manager, callback, mediator, user, region, slot
            )
            return
        else:
            dialog_manager.dialog_data["held_warning"] = item_id
            await callback.answer(
                "💰 Этот слот платный. Нажмите ещё раз для продолжения к оплате.",
                show_alert=True,
            )
        return

    if result.pricing_changed_to_converted:
        amount = region.settings.paid_slot_price

        if dialog_manager.dialog_data.get("paid_slot_confirm") == item_id:
            dialog_manager.dialog_data.pop("paid_slot_confirm", None)

            if user.balance >= amount:
                await mediator.handle(
                    ConfirmPaidSlotFromBalanceRequest(
                        user_id=user.id,
                        slot=slot,
                        amount=amount,
                    )
                )
                dialog_manager.dialog_data["region_id"] = slot.region_id
                dialog_manager.dialog_data["slot_day"] = slot.local_day.isoformat()
                dialog_manager.dialog_data["slot_time"] = slot.local_time.strftime(
                    "%H:%M"
                )
                dialog_manager.dialog_data["is_paid"] = True

                await callback.answer(
                    f"💰 Списано {amount} руб. с баланса.", show_alert=True
                )
                await dialog_manager.next()
                return
            else:
                await _start_slot_payment(
                    dialog_manager, callback, mediator, user, region, slot
                )
                return
        else:
            dialog_manager.dialog_data["paid_slot_confirm"] = item_id
            await callback.answer(
                f"💰 Этот слот платный ({amount} руб.). "
                "Нажмите ещё раз для подтверждения покупки.",
                show_alert=True,
            )
            return

    dialog_manager.dialog_data["region_id"] = slot.region_id
    dialog_manager.dialog_data["slot_day"] = slot.local_day.isoformat()
    dialog_manager.dialog_data["slot_time"] = slot.local_time.strftime("%H:%M")
    dialog_manager.dialog_data["is_paid"] = result.pricing_changed_to_converted

    await dialog_manager.next()


async def _start_slot_payment(
    dialog_manager: DialogManager,
    callback: CallbackQuery,
    mediator: Mediator,
    user: UserDTO,
    region: RegionDTO,
    slot: SlotKey,
) -> None:
    data = dialog_manager.dialog_data

    ad_type: AdType = data["ad_type"]

    if data.get("reuse_ad"):
        existing_ad_id: int = data["existing_ad_id"]
        existing_ad: AdDTO = await mediator.handle(
            GetByIdAdRequest(ad_id=existing_ad_id)
        )
        c = existing_ad.content

        ad: AdDTO = (
            existing_ad  # объявление уже существует, повторно создавать не нужно
        )
        plate = c.plate_number if c else data.get("plate", "")
        city = c.city if c else ""
        price_raw = c.price.value if c and c.price else None
        contacts = c.contacts if c and c.contacts else None
        media_file_id = c.image_file_id if c else None

    else:
        plate: str = data["plate"]
        city: str = data.get("city", "")
        price_raw = data.get("price")
        phone: str = data.get("phone") or data.get("current_phone", "")
        contacts = Contacts.from_user(username=user.username, phone=phone)

        media: MediaAttachment = data.get("media")
        if not media:
            media = await mediator.handle(
                EnsureAdImageRefRequest(
                    plate=plate,
                    channel_username=data["channel_username"],
                    chat_id=callback.from_user.id,
                )
            )
        media_file_id = media.file_id.file_id if media and media.file_id else None

        ad: AdDTO = await mediator.handle(
            CreateAdDraftRequest(
                user_id=user.id,
                region_id=user.region_id,
                ad_type=ad_type,
                status=AdStatus.DRAFT,
            )
        )
        await mediator.handle(
            UpdateAdContentRequest(
                ad_id=ad.id,
                plate_number=plate,
                city=city,
                price=Price(int(price_raw)) if price_raw else None,
                contacts=contacts,
                image_file_id=media_file_id,
            )
        )

    await start_payment(
        dialog_manager,
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        params=PaymentStartParams(
            purpose=PaymentPurpose.SLOT,
            amount=region.settings.paid_slot_price,
            description="Оплата платного слота",
            return_state="CreateAdSG:confirm",
            return_data={
                "ad_id": ad.id,
                "slot": {
                    "region_id": user.region_id,
                    "local_day": slot.local_day.isoformat(),
                    "local_time": slot.local_time.isoformat(),
                },
                "is_paid": True,
            },
        ),
    )


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
    hold_valid = await mediator.handle(
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


@inject
async def on_service_paid_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    start_data = dialog_manager.start_data or {}
    pub_id: int = dialog_manager.dialog_data.get("publication_id") or start_data.get("publication_id")
    service_type = PublicationServiceType(item_id)

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=callback.from_user.id))

    logger.info(
        f"[ServiceSelected] user_id={user.id} pub_id={pub_id} service={service_type}"
    )

    pub: PublicationDTO = await mediator.handle(
        GetPublicationByIdRequest(publication_id=pub_id)
    )
    bought_types = {
        s.type for s in pub.services if s.status == PublicationServiceStatus.ACTIVE
    }
    if item_id in bought_types:
        await callback.answer("⚠️ Эта услуга уже активна.", show_alert=True)
        return

    services: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )
    service = next((s for s in services if s.type == service_type), None)
    if not service:
        await callback.answer("❌ Услуга не найдена.", show_alert=True)
        return

    pending_key = "pending_service"
    if dialog_manager.dialog_data.get(pending_key) != item_id:
        dialog_manager.dialog_data[pending_key] = item_id
        duration = f" на {service.duration_days} дн." if service.duration_days else ""
        await callback.answer(
            f"💳 {service.title}{duration}\n"
            f"Стоимость: {service.price} руб.\n\n"
            f"Нажмите ещё раз для подтверждения.",
            show_alert=True,
        )
        logger.info(
            f"[ServiceSelected:confirm] waiting second click for {service_type}"
        )
        return
    logger.info(
        f"[ServiceSelected:second_click] service={service_type} user_id={user.id}"
    )

    price_decimal = Decimal(service.price)
    dialog_manager.dialog_data.pop(pending_key, None)

    if user.balance >= price_decimal:
        # хватает баланса — покупаем сразу как раньше
        try:
            await mediator.handle(
                BuyPublicationServiceRequest(
                    publication_id=pub_id,
                    service_type=service_type,
                    user_id=user.id,
                )
            )
        except InsufficientBalance:
            await start_payment(
                dialog_manager,
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                params=PaymentStartParams(
                    purpose=PaymentPurpose.PUBLICATION_SERVICE,
                    amount=price_decimal,
                    description=service.title,
                    purpose_id=pub_id,
                    return_state="CreateAdSG:publication_service",
                    return_data={"publication_id": pub_id},
                    meta={"service_type": service_type.value},
                ),
            )
            return

        pub = await mediator.handle(GetPublicationByIdRequest(publication_id=pub_id))

        if service_type == PublicationServiceType.PRIORITY_PUBLISH:
            logger.info(f"[ServiceSelected:priority] publishing now pub_id={pub_id}")
            await mediator.handle(
                PriorityPublishPublicationRequest(publication_id=pub_id)
            )
        elif pub.status == PublicationStatus.PUBLISHED:
            logger.info(
                f"[ServiceSelected:apply_to_published] pub_id={pub_id} service={service_type}"
            )
            await mediator.handle(
                ApplyServiceToPublishedRequest(
                    publication_id=pub_id,
                    service_type=service_type,
                )
            )

        logger.info(
            f"[ServiceSelected:done] user_id={user.id} pub_id={pub_id} service={service_type}"
        )
        await callback.answer(f"✅ {service.title} активирована!", show_alert=True)
    else:
        await start_payment(
            dialog_manager,
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            params=PaymentStartParams(
                purpose=PaymentPurpose.PUBLICATION_SERVICE,
                amount=price_decimal,
                description=service.title,
                purpose_id=pub_id,
                return_state="CreateAdSG:publication_service",
                return_data={"publication_id": pub_id},
                meta={"service_type": service_type.value},
            ),
        )
