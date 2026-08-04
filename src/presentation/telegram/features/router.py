from aiogram import Router
from aiogram.types import CallbackQuery

fallback_router = Router()


@fallback_router.callback_query()
async def on_unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer(
        "⚠️ Это меню устарело. Отправьте /start, чтобы начать заново.",
        show_alert=True,
    )
