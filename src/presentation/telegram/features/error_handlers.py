import logging
import traceback
import sentry_sdk
from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.api.exceptions import UnknownIntent, OutdatedIntent


async def on_input_error(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(f"❌ {error}")


logger = logging.getLogger(__name__)
router = Router()


# @router.errors()
# async def on_region_disabled_error(
#     event: ErrorEvent,
#     dialog_manager: DialogManager,
# ) -> bool:
#     if not isinstance(event.exception, RegionDisabledError):
#         return False

#     update = event.update
#     if update.message:
#         user_id = update.message.from_user.id
#     elif update.callback_query:
#         user_id = update.callback_query.from_user.id
#     else:
#         return False

#     bot: Bot = dialog_manager.middleware_data["bot"]
#     await bot.send_message(
#         chat_id=user_id,
#         text="🚫 <b>Регион временно отключён администратором.</b>\n\nВыберите другой регион через /start",
#     )

#     try:
#         await dialog_manager.reset_stack()
#     except Exception:
#         pass

#     return True


async def handle_error(
    event: ErrorEvent,
    dialog_manager: DialogManager | None = None,
) -> None:
    exc = event.exception
    update = event.update

    if isinstance(exc, (UnknownIntent, OutdatedIntent)):
        try:
            if update.callback_query:
                await update.callback_query.answer(
                    "⚠️ Это меню устарело. Отправьте /start, чтобы начать заново.",
                    show_alert=True,
                )
            elif update.message:
                await update.message.answer(
                    "⚠️ Это меню устарело. Отправьте /start, чтобы начать заново."
                )
        except Exception:
            logger.exception("[UnknownIntent] не удалось ответить пользователю")

        logger.info(
            "[UnknownIntent] stale dialog interaction user_id=%s",
            update.callback_query.from_user.id
            if update.callback_query
            else (update.message.from_user.id if update.message else None),
        )
        return

    user_id = None
    chat_id = None
    action = None

    if update.message:
        user_id = update.message.from_user.id if update.message.from_user else None
        chat_id = update.message.chat.id
        action = f"message: {update.message.text or update.message.content_type}"
    elif update.callback_query:
        cq = update.callback_query
        user_id = cq.from_user.id if cq.from_user else None
        chat_id = cq.message.chat.id if cq.message else None
        action = f"callback: {cq.data}"

    dialog_state = None
    if dialog_manager is not None:
        try:
            dialog_state = dialog_manager.current_context().state
        except Exception:
            dialog_state = "<no active dialog>"

    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    logger.error(
        "[UnhandledError] user_id=%s chat_id=%s action=%s dialog_state=%s "
        "exc_type=%s exc_msg=%s\n%s",
        user_id,
        chat_id,
        action,
        dialog_state,
        type(exc).__name__,
        exc,
        tb,
    )

    sentry_sdk.set_context(
        "telegram",
        {
            "user_id": user_id,
            "chat_id": chat_id,
            "action": action,
            "dialog_state": str(dialog_state),
        },
    )
    sentry_sdk.capture_exception(exc)

    try:
        if update.message:
            await update.message.answer(
                "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню, или отправьте боту команду: /start"
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню, или отправьте боту команду: /start",
                show_alert=True,
            )
    except Exception:
        logger.exception(
            "[UnhandledError] не удалось отправить сообщение об ошибке пользователю"
        )
