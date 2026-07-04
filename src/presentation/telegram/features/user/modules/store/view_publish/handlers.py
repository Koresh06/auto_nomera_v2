from datetime import date, time

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka.integrations.aiogram_dialog import inject, FromDishka

from src.application.dtos.publication import PublicationDTO
from src.domain.value_objects.slot_key import SlotKey
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.application.use_cases.slots.check_hold import CheckHoldRequest
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdRequest,
)
from .states import StoreViewPublishSG


@inject
async def on_confirm_publish(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data
    ad_id: int = data.get("ad_id") or dialog_manager.start_data.get("ad_id")
    region_id: int = data.get("region_id") or dialog_manager.start_data.get("region_id")
    slot_day = data.get("slot_day") or dialog_manager.start_data.get("slot_day")
    slot_time = data.get("slot_time") or dialog_manager.start_data.get("slot_time")

    slot: SlotKey = SlotKey(
        region_id=region_id,
        local_day=date.fromisoformat(slot_day),
        local_time=time.fromisoformat(slot_time),
    )

    user: UserDTO = await mediator.handle(
        GetTgIdRequest(tg_id=callback.from_user.id)
    )

    hold_valid: bool = await mediator.handle(
        CheckHoldRequest(
            region_id=slot.region_id,
            slot=slot,
            user_id=user.id,
        )
    )
    if not hold_valid:
        await callback.answer(
            "⏰ Время ожидания подтверждения истекло. Выберите слот заново.",
            show_alert=True,
        )
        await dialog_manager.switch_to(StoreViewPublishSG.calendar)
        return

    pub: PublicationDTO = await mediator.handle(
        FinalizeAndScheduleExistingAdRequest(
            ad_id=ad_id,
            slot=slot,
            user_id=user.id,
            payment_confirmed=data.get("is_paid", False),
        )
    )

    data["publication_id"] = pub.id
    await dialog_manager.next()