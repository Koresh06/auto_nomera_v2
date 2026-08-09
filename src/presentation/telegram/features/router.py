from aiogram import Router
from aiogram.types import CallbackQuery

fallback_router = Router()


@fallback_router.callback_query()
async def on_unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer(
        "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню, или отправьте боту команду: /start",
        show_alert=True,
    )
