"""Фолбэк редактирования: старое сообщение в стеке диалога разошлось с
реальным (текст vs фото) — удаляем и шлём окно заново."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from src.presentation.telegram.common import custom_message_manager as cmm

METHOD = EditMessageText(text="x")


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr(cmm.PlateGenerator, "load", staticmethod(lambda: None))
    return cmm.CustomMessageManager()


async def test_no_text_to_edit_falls_back_to_resend(manager, monkeypatch):
    err = TelegramBadRequest(
        METHOD, "Bad Request: there is no text in the message to edit"
    )
    monkeypatch.setattr(
        cmm.MessageManager, "edit_message_safe", AsyncMock(side_effect=err)
    )
    sent = MagicMock()
    manager.remove_message_safe = AsyncMock()
    manager.send_message = AsyncMock(return_value=sent)

    result = await manager.edit_message_safe(MagicMock(), MagicMock(), MagicMock())

    assert result is sent
    manager.remove_message_safe.assert_awaited_once()


async def test_other_bad_request_is_reraised(manager, monkeypatch):
    err = TelegramBadRequest(METHOD, "Bad Request: chat not found")
    monkeypatch.setattr(
        cmm.MessageManager, "edit_message_safe", AsyncMock(side_effect=err)
    )
    manager.send_message = AsyncMock()

    with pytest.raises(TelegramBadRequest):
        await manager.edit_message_safe(MagicMock(), MagicMock(), MagicMock())
    manager.send_message.assert_not_awaited()
