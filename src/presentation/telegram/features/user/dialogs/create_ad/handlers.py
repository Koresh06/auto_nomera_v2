from __future__ import annotations

from datetime import date, time

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Select

from dishka.integrations.aiogram_dialog import inject
from dishka.integrations.aiogram import FromDishka

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
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

from src.domain.enums.ad import AdType
from src.domain.value_objects.slot_key import SlotKey

from .states import CreateAdSG


REGION_ID_DEV = 1


@inject
async def on_plate_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    if "ad_id" not in dialog_manager.dialog_data:
        dto: AdDTO = await mediator.handle(
            CreateAdDraftRequest(
                user_id=message.from_user.id,
                region_id=REGION_ID_DEV,
                ad_type=AdType.SALE,
            )
        )
        dialog_manager.dialog_data["ad_id"] = dto.id

    ad_id = dialog_manager.dialog_data["ad_id"]
    await mediator.handle(UpdateAdContentRequest(ad_id=ad_id, plate_number=value))
    await dialog_manager.switch_to(CreateAdSG.city)


@inject
async def on_city_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    ad_id = dialog_manager.dialog_data["ad_id"]
    await mediator.handle(UpdateAdContentRequest(ad_id=ad_id, city=value))
    await dialog_manager.switch_to(CreateAdSG.price)


@inject
async def on_price_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    ad_id = dialog_manager.dialog_data["ad_id"]
    await mediator.handle(UpdateAdContentRequest(ad_id=ad_id, price_text=value))
    await dialog_manager.switch_to(CreateAdSG.contacts)


@inject
async def on_contacts_success(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    ad_id = dialog_manager.dialog_data["ad_id"]
    await mediator.handle(UpdateAdContentRequest(ad_id=ad_id, contacts=value))

    # финализация (если фото нет — проставит my://... для генератора)
    await mediator.handle(FinalizeAdRequest(ad_id=ad_id, chat_id=message.chat.id))

    # создаём publication
    pub: PublicationDTO = await mediator.handle(
        CreatePublicationFromAdRequest(ad_id=ad_id)
    )
    dialog_manager.dialog_data["publication_id"] = pub.id

    await dialog_manager.switch_to(CreateAdSG.calendar)


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
