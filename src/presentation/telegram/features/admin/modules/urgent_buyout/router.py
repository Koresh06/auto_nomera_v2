import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from dishka.integrations.aiogram import inject, FromDishka

from src.application.exceptions.ad import (
    AdAlreadyProcessedException,
    AdNotFoundException,
)
from src.application.mediator import Mediator
from src.application.use_cases.ad.approve_urgent_buyout import (
    ApproveUrgentBuyoutRequest,
)
from src.application.use_cases.ad.eject_urgent_buyout import RejectUrgentBuyoutRequest
from src.presentation.telegram.keyboards.urgent_moderation import (
    UrgentModerationAction,
    UrgentModerationCD,
)


logger = logging.getLogger(__name__)


router = Router()


@router.callback_query(
    UrgentModerationCD.filter(F.action == UrgentModerationAction.APPROVE)
)
@inject
async def approve_urgent_buyout(
    callback: CallbackQuery,
    callback_data: UrgentModerationCD,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        await mediator.handle(ApproveUrgentBuyoutRequest(ad_id=callback_data.ad_id))
        await callback.answer("✅ Заявка одобрена!", show_alert=True)
    except AdNotFoundException:
        await callback.answer("⚠️ Заявка устарела или удалена.", show_alert=True)
    except AdAlreadyProcessedException:
        await callback.answer(
            "⚠️ Заявка уже обработана другим администратором.", show_alert=True
        )
    finally:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass


@router.callback_query(
    UrgentModerationCD.filter(F.action == UrgentModerationAction.REJECT)
)
@inject
async def reject_urgent_buyout(
    callback: CallbackQuery,
    callback_data: UrgentModerationCD,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        await mediator.handle(RejectUrgentBuyoutRequest(ad_id=callback_data.ad_id))
        await callback.answer("❌ Заявка отклонена.", show_alert=True)
    except AdNotFoundException:
        await callback.answer("⚠️ Заявка устарела или удалена.", show_alert=True)
    except AdAlreadyProcessedException:
        await callback.answer(
            "⚠️ Заявка уже обработана другим администратором.", show_alert=True
        )
    finally:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
