from datetime import date, time
from decimal import Decimal
import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.api.entities import MediaAttachment

from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.publication import PublicationDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.use_cases.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceRequest,
)
from src.application.use_cases.ad.create_ad_draft import CreateAdDraftRequest
from src.application.use_cases.ad.ensure_ad_image_ref import EnsureAdImageRefRequest
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest
from src.application.use_cases.ad.update_ad_content import UpdateAdContentRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedRequest,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
)
from src.application.use_cases.service_difinition.get_all import GetAllServicesRequest
from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationRequest,
)
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest
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
from src.domain.services.publication.limiter import LimitCheckResult
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.slot_reservation_service import HoldResult
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.ad import AdDTO
from src.application.dtos.region import RegionDTO
from src.application.use_cases.publication.check_limiter import (
    CheckPublicationLimitRequest,
)
from src.application.use_cases.region.get_by_id import IdRegionRequest
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.slots.hold_slot import HoldSlotRequest
from src.presentation.telegram.features.user.modules.payment.helpers import (
    PaymentStartParams,
    start_payment,
)

logger = logging.getLogger(__name__)


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
    plate: str | None = dialog_manager.dialog_data.get("plate")

    region: RegionDTO = await mediator.handle(IdRegionRequest(user.region_id))
    publish_at_utc = PublishTimeResolver().resolve_publish_at_utc(
        tz=region.timezone, slot=slot
    )
    try:
        result: HoldResult = await mediator.handle(
            HoldSlotRequest(
                region_id=user.region_id,
                slot=slot,
                user_id=user.id,
            )
        )

        is_paid_slot = result.is_system_paid or result.is_converted
        logger.info(
            "[on_pick_slot] is_paid_slot=%s, is_converted=%s",
            result.is_system_paid,
            result.is_converted,
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

    if not is_paid_slot:
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
            await mediator.handle(
                ReleaseHoldRequest(
                    slot=slot,
                    user_id=user.id,
                )
            )

            await callback.answer(
                limit_result.reason,
                show_alert=True,
            )
            return

    if is_paid_slot:
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
    dialog_manager.dialog_data["is_paid"] = is_paid_slot

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

    if ad_type == AdType.STORE.value:
        return_state = "StoreViewPublishSG:confirm"
    else:
        return_state = "CreateAdSG:confirm"

    if ad_type == AdType.STORE.value:
        store_ad_id: int = data["ad_id"]
        ad: AdDTO = await mediator.handle(GetByIdAdRequest(ad_id=store_ad_id))

    elif data.get("reuse_ad"):
        existing_ad_id: int = data["existing_ad_id"]
        existing_ad: AdDTO = await mediator.handle(
            GetByIdAdRequest(ad_id=existing_ad_id)
        )
        c = existing_ad.content

        ad: AdDTO = existing_ad
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
            return_state=return_state,
            return_data={
                "ad_id": ad.id,
                "slot": {
                    "region_id": user.region_id,
                    "slot_day": slot.local_day.isoformat(),
                    "slot_time": slot.local_time.isoformat(),
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
    tg_id = callback.from_user.id
    data = dialog_manager.dialog_data

    is_slot_paid = data.get("is_paid") or dialog_manager.start_data.get("is_paid")

    back_warning = data.get("back_warning")

    if is_slot_paid and back_warning != tg_id:
        data["back_warning"] = tg_id

        await callback.answer(
            "Внимание! При отмене вы потеряете доступ "
            "к платному слоту. Для подтверждения возврата нажмите кнопку снова.",
            show_alert=True,
        )
        return

    data.pop("back_warning", None)

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=dialog_manager.event.from_user.id)
    )

    region_id = data.get("region_id") or dialog_manager.start_data.get("region_id")
    slot_day = data.get("slot_day") or dialog_manager.start_data.get("slot_day")
    slot_time = data.get("slot_time") or dialog_manager.start_data.get("slot_time")

    if region_id and slot_day and slot_time:
        slot = SlotKey(
            region_id=region_id,
            local_day=date.fromisoformat(slot_day),
            local_time=time.fromisoformat(slot_time),
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
    data.pop("is_paid", None)

    await dialog_manager.done()


@inject
async def on_service_paid_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    start_data = dialog_manager.start_data or {}
    pub_id: int = dialog_manager.dialog_data.get("publication_id") or start_data.get(
        "publication_id"
    )
    ad_type: AdType = dialog_manager.dialog_data.get("ad_type")
    service_type = PublicationServiceType(item_id)

    if ad_type == AdType.STORE.value:
        return_state = "StoreViewPublishSG:publication_service"
    else:
        return_state = "CreateAdSG:publication_service"

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=callback.from_user.id))

    logger.info(
        f"[ServiceSelected] user_id={user.id} pub_id={pub_id} service={service_type}"
    )

    pub: PublicationDTO = await mediator.handle(
        GetPublicationByIdRequest(publication_id=pub_id)
    )
    bought_types = {
        s.type
        for s in pub.services
        if s.status in (PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED)
    }
    logger.info(
        f"[ServiceSelected:check] service_type={service_type} "
        f"pub.services={[(s.type, s.status) for s in pub.services]} "
        f"bought_types={bought_types}"
    )

    if service_type in bought_types:
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
                    return_state=return_state,
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
                return_state=return_state,
                return_data={"publication_id": pub_id},
                meta={"service_type": service_type.value},
            ),
        )
