import logging
import traceback
import sentry_sdk
from aiogram import Router
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import ErrorEvent, Update
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.api.exceptions import UnknownIntent, OutdatedIntent

from src.application.exceptions.user import UserNotFoundException


async def on_input_error(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(f"❌ {error}")


logger = logging.getLogger(__name__)
router = Router()

ERROR_TEXT = (
    "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню, "
    "или отправьте боту команду: /start"
)

# сбои на стороне Telegram (таймауты, 5xx, флуд-контроль) — не баг бота,
# в Sentry не шлём и полный traceback не пишем
_TRANSIENT_TG_ERRORS = (TelegramNetworkError, TelegramServerError, TelegramRetryAfter)


async def _reply_error(update: Update, tag: str) -> None:
    try:
        if update.callback_query:
            await update.callback_query.answer(ERROR_TEXT, show_alert=True)
        elif update.message:
            await update.message.answer(ERROR_TEXT)
    except TelegramAPIError as e:
        # «query is too old», бот заблокирован, Telegram недоступен — ответить
        # пользователю уже нельзя, и это не повод для второго traceback'а
        logger.warning("[%s] не удалось ответить пользователю: %s", tag, e)
    except Exception:
        logger.exception("[%s] не удалось ответить пользователю", tag)


def _event_user_id(update: Update) -> int | None:
    if update.callback_query:
        return update.callback_query.from_user.id
    if update.message and update.message.from_user:
        return update.message.from_user.id
    return None


async def handle_error(
    event: ErrorEvent,
    dialog_manager: DialogManager | None = None,
) -> None:
    exc = event.exception
    update = event.update

    if isinstance(exc, (UnknownIntent, OutdatedIntent)):
        await _reply_error(update, "UnknownIntent")
        logger.info(
            "[UnknownIntent] stale dialog interaction user_id=%s",
            _event_user_id(update),
        )
        return

    if isinstance(exc, UserNotFoundException):
        await _reply_error(update, "UserNotFound")
        logger.info(
            "[UserNotFound] незарегистрированный юзер user_id=%s",
            _event_user_id(update),
        )
        return

    if isinstance(exc, TelegramForbiddenError):
        # пользователь заблокировал бота — отвечать некому
        logger.info(
            "[Forbidden] user_id=%s заблокировал бота: %s",
            _event_user_id(update),
            exc,
        )
        return

    if isinstance(exc, _TRANSIENT_TG_ERRORS):
        logger.warning(
            "[TelegramUnavailable] user_id=%s exc_type=%s exc_msg=%s",
            _event_user_id(update),
            type(exc).__name__,
            exc,
        )
        await _reply_error(update, "TelegramUnavailable")
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

    await _reply_error(update, "UnhandledError")
