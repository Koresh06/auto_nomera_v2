from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class UrgentModerationCD(CallbackData, prefix="urgent_mod"):
    action: str
    ad_id: int


def build_urgent_moderation_kb(ad_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Одобрить",
        callback_data=UrgentModerationCD(action="approve", ad_id=ad_id).pack(),
    )
    kb.button(
        text="❌ Отклонить",
        callback_data=UrgentModerationCD(action="reject", ad_id=ad_id).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()