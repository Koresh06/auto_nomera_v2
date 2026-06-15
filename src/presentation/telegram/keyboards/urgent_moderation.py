from enum import StrEnum
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class UrgentModerationAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class UrgentModerationCD(CallbackData, prefix="urgent_mod"):
    action: UrgentModerationAction
    ad_id: int


async def build_urgent_moderation_kb(ad_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Одобрить",
        callback_data=UrgentModerationCD(
            action=UrgentModerationAction.APPROVE, ad_id=ad_id,
        ).pack(),
        style="success",
    )
    kb.button(
        text="❌ Отклонить",
        callback_data=UrgentModerationCD(
            action=UrgentModerationAction.REJECT, ad_id=ad_id,
        ).pack(),
        style="danger",
    )
    kb.adjust(1)
    return kb.as_markup()
