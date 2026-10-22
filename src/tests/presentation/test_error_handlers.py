"""Глобальный error-хендлер бота: сбои Telegram — не баги бота."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramServerError,
)
from aiogram.methods import SendMessage

from src.presentation.telegram.features import error_handlers
from src.presentation.telegram.features.error_handlers import handle_error

METHOD = SendMessage(chat_id=1, text="x")


def _callback_event(exc: Exception, *, answer_exc: Exception | None = None):
    cq = MagicMock()
    cq.from_user.id = 42
    cq.message.chat.id = 42
    cq.data = "slot:x"
    cq.answer = AsyncMock(side_effect=answer_exc)
    update = MagicMock(message=None, callback_query=cq)
    return MagicMock(exception=exc, update=update), cq


@pytest.fixture
def sentry(monkeypatch):
    capture = MagicMock()
    monkeypatch.setattr(error_handlers.sentry_sdk, "capture_exception", capture)
    return capture


async def test_forbidden_is_info_and_no_reply(sentry, caplog):
    event, cq = _callback_event(TelegramForbiddenError(METHOD, "bot was blocked"))
    caplog.set_level(logging.INFO)

    await handle_error(event)

    cq.answer.assert_not_awaited()
    sentry.assert_not_called()
    assert all(r.levelno < logging.WARNING for r in caplog.records)


@pytest.mark.parametrize(
    "exc",
    [
        TelegramNetworkError(METHOD, "Request timeout error"),
        TelegramServerError(METHOD, "Bad Gateway"),
    ],
)
async def test_transient_telegram_errors_skip_sentry(exc, sentry, caplog):
    event, cq = _callback_event(exc)

    await handle_error(event)

    sentry.assert_not_called()
    cq.answer.assert_awaited_once()
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_failed_reply_is_warning_without_traceback(sentry, caplog):
    too_old = TelegramBadRequest(METHOD, "query is too old")
    event, _ = _callback_event(ValueError("boom"), answer_exc=too_old)

    await handle_error(event)

    sentry.assert_called_once()
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1 and "[UnhandledError]" in errors[0].getMessage()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and warnings[0].exc_info is None
