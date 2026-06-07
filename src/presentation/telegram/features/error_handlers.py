import logging
from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput


async def on_input_error(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(f"❌ {error}")



logger = logging.getLogger(__name__)
router = Router()

@router.errors()
async def handle_error(event: ErrorEvent) -> None:
    logger.error(f"Error: {event.exception}", exc_info=event.exception)
    
    update = event.update
    if update.message:
        await update.message.answer(
            "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню /start"
        )
    elif update.callback_query:
        await update.callback_query.answer(
            "⚠️ Произошла ошибка. Попробуйте ещё раз.",
            show_alert=True,
        )