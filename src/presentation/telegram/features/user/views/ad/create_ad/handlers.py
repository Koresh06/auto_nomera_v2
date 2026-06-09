from decimal import Decimal
import logging

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from aiogram_dialog.widgets.kbd import Select, Button
from aiogram_dialog.widgets.kbd.select import OnItemClick
from aiogram_dialog.api.entities import MediaAttachment

from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.use_cases.ad.find_by_plate import FindAdByPlateRequest
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication.reuse_ad_and_schedule import ReuseAdAndScheduleRequest
from src.application.use_cases.publication_service.apply_service import ApplyServiceToPublishedRequest
from src.application.use_cases.publication_service.buy_publication_service import BuyPublicationServiceRequest
from src.application.use_cases.publication_service.get_all import GetAllServicesRequest
from src.application.use_cases.publication_service.priority_publish_publication import PriorityPublishPublicationRequest
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.exceptions.slot_reservation import  SlotAlreadyConverted, SlotAlreadyHeld, SlotHoldNotFound, SlotHoldOwnerMismatch
from src.domain.services.ad.plate_validator import validate_plate
from src.domain.services.slots.slot_reservation_service import HoldResult
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.user import UpdateUserDTO, UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.application.mediator import Mediator
from src.application.use_cases.publication.create_ad_publication import CreateAndScheduleAdRequest
from src.application.use_cases.slots.hold_slot import HoldSlotRequest
from src.application.use_cases.slots.release_hold import ReleaseHoldRequest
from src.application.use_cases.user.update import UpdateUserRequest
from src.presentation.telegram.features.user.views.ad.create_ad.states import CreateAdSG


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
    tg_id = dialog_manager.event.from_user.id

    try:
        validated = validate_plate(value, allow_mask=allow_mask)
    except ValueError as e:
        await message.answer(str(e))
        return

    dialog_manager.dialog_data["plate"] = validated

    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=tg_id))
    dialog_manager.dialog_data["user"] = user

    if ad_type != AdType.BUY:
        existing_ad: AdDTO | None = await mediator.handle(
            FindAdByPlateRequest(
                user_id=user.id,
                region_id=user.region_id,
                plate_number=validated,
            )
        )
        if existing_ad:
            dialog_manager.dialog_data["existing_ad_id"] = existing_ad.id
            dialog_manager.dialog_data["existing_ad"] = existing_ad
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
    slot: SlotKey = data["slot"]

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
        ad_type: AdType = data["ad_type"]
        plate: str = data["plate"]
        city: str = data["city"]
        price: Price = Price(int(data["price"]))
        phone: str = data["phone"]
        media: MediaAttachment = data["media"]
        contacts = Contacts.from_user(username=user.username, phone=phone)

        pub: PublicationDTO = await mediator.handle(
            CreateAndScheduleAdRequest(
                user_id=user.id,
                region_id=region_id,
                ad_type=ad_type,
                plate=plate,
                city=city,
                price=price,
                contacts=contacts,
                image_file_id=media.file_id.file_id if media and media.file_id else None,
                slot=slot,
                chat_id=tg_id,
            )
        )

    data["publication_id"] = pub.id

    logger.info("[on_confirm:done] ad created/reused")
    await dialog_manager.next()


@inject
async def on_service_paid_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    user: UserDTO = dialog_manager.dialog_data["user"]
    pub_id: int = dialog_manager.dialog_data["publication_id"]
    service_type = PublicationServiceType(item_id)

    logger.info(f"[ServiceSelected] user_id={user.id} pub_id={pub_id} service={service_type}")

    # проверяем уже куплена ли
    pub: PublicationDTO = await mediator.handle(GetPublicationByIdRequest(publication_id=pub_id))
    bought_types = {s["type"] for s in pub.services if s["status"] == "active"}
    if item_id in bought_types:
        await callback.answer("⚠️ Эта услуга уже активна.", show_alert=True)
        return

    # получаем определение услуги
    services: list[ServiceDefinitionDTO] = await mediator.handle(GetAllServicesRequest())
    service = next((s for s in services if s.type == service_type), None)
    if not service:
        await callback.answer("❌ Услуга не найдена.", show_alert=True)
        return

    # двойное подтверждение
    pending_key = "pending_service"
    if dialog_manager.dialog_data.get(pending_key) != item_id:
        dialog_manager.dialog_data[pending_key] = item_id
        duration = f" на {service.duration_days} дн." if service.duration_days else ""
        await callback.answer(
            f"💳 {service.title}{duration}\n"
            f"Стоимость: {service.price // 100} руб.\n\n"
            f"Нажмите ещё раз для подтверждения.",
            show_alert=True,
        )
        logger.info(f"[ServiceSelected:confirm] waiting second click for {service_type}")
        return
    logger.info(f"[ServiceSelected:second_click] service={service_type} user_id={user.id}")

    # проверяем баланс
    price_decimal = Decimal(service.price) / 100
    if user.balance < price_decimal:
        diff = int(price_decimal - user.balance)
        logger.warning(f"[ServiceSelected:insufficient] user_id={user.id} balance={user.balance} need={price_decimal}")
        await callback.answer(
            f"😔 Недостаточно средств.\n"
            f"Пополните баланс на {diff} руб. и попробуйте снова.",
            show_alert=True,
        )
        dialog_manager.dialog_data.pop(pending_key, None)
        return

    # покупаем
    logger.info(f"[ServiceSelected:buy] user_id={user.id} pub_id={pub_id} service={service_type}")
    await mediator.handle(
        BuyPublicationServiceRequest(
            publication_id=pub_id,
            service_type=service_type,
            user_id=user.id,
        )
    )

    # получаем актуальный статус публикации
    pub = await mediator.handle(GetPublicationByIdRequest(publication_id=pub_id))

    if service_type == PublicationServiceType.PRIORITY_PUBLISH:
        logger.info(f"[ServiceSelected:priority] publishing now pub_id={pub_id}")
        await mediator.handle(PriorityPublishPublicationRequest(publication_id=pub_id))

    elif pub.status == PublicationStatus.PUBLISHED:
        logger.info(f"[ServiceSelected:apply_to_published] pub_id={pub_id} service={service_type}")
        await mediator.handle(
            ApplyServiceToPublishedRequest(
                publication_id=pub_id,
                service_type=service_type,
            )
        )

    dialog_manager.dialog_data.pop(pending_key, None)
    logger.info(f"[ServiceSelected:done] user_id={user.id} pub_id={pub_id} service={service_type}")
    await callback.answer(f"✅ {service.title} активирована!", show_alert=True)