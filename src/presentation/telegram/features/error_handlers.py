import logging
from aiogram import Bot, Router
from aiogram.types import ErrorEvent
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput

from src.domain.exceptions.region import RegionDisabledError


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
async def on_region_disabled_error(
    event: ErrorEvent,
    dialog_manager: DialogManager,
) -> bool:
    if not isinstance(event.exception, RegionDisabledError):
        return False

    update = event.update
    if update.message:
        user_id = update.message.from_user.id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        return False

    bot: Bot = dialog_manager.middleware_data["bot"]
    await bot.send_message(
        chat_id=user_id,
        text="🚫 <b>Регион временно отключён администратором.</b>\n\nВыберите другой регион через /start",
    )

    try:
        await dialog_manager.reset_stack()
    except Exception:
        pass

    return True


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
