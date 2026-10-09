"""AiogramNotificationService: доставка и обработка ошибок Telegram.

Бот-заглушка отвечает на методы так же, как Bot API: успехом или
исключениями aiogram (бот заблокирован, flood-лимит, bad request)."""

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage

from src.infrastructure.telegram import notification_service as module
from src.infrastructure.telegram.notification_service import (
    AiogramNotificationService,
)

M = SendMessage(chat_id=1, text="x")


def forbidden():
    return TelegramForbiddenError(method=M, message="bot was blocked by the user")


def flood(seconds=1):
    return TelegramRetryAfter(method=M, message="flood", retry_after=seconds)


def bad_request():
    return TelegramBadRequest(method=M, message="chat not found")


class FakeBot:
    """Сценарий ответов: chat_id -> список исключений/None по попыткам."""

    def __init__(self, script: dict | None = None) -> None:
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.sent: list[tuple[str, int, dict]] = []

    def _next(self, chat_id):
        outcomes = self.script.get(chat_id)
        if outcomes:
            exc = outcomes.pop(0)
            if exc is not None:
                raise exc

    async def send_message(self, *, chat_id, text, **kw):
        self._next(chat_id)
        self.sent.append(("message", chat_id, {"text": text, **kw}))

    async def send_photo(self, *, chat_id, photo, caption, **kw):
        self._next(chat_id)
        self.sent.append(("photo", chat_id, {"photo": photo, "caption": caption}))

    async def copy_message(self, *, chat_id, from_chat_id, message_id):
        self._next(chat_id)
        self.sent.append(("copy", chat_id, {"from": from_chat_id, "id": message_id}))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)
    return slept


async def test_notify_admins_sends_photo_or_text_to_every_admin():
    bot = FakeBot()
    svc = AiogramNotificationService(bot=bot, admin_ids=[1, 2])

    await svc.notify_admins(text="hi")
    await svc.notify_admins(text="cap", photo_id="ph")

    assert [(k, c) for k, c, _ in bot.sent] == [
        ("message", 1),
        ("message", 2),
        ("photo", 1),
        ("photo", 2),
    ]


async def test_notify_admins_survives_each_kind_of_failure(no_sleep):
    bot = FakeBot(
        {
            1: [forbidden()],
            2: [flood(7), None],  # повтор после ожидания успешен
            3: [bad_request()],
            4: [RuntimeError("boom")],
            5: [None],
        }
    )
    svc = AiogramNotificationService(bot=bot, admin_ids=[1, 2, 3, 4, 5])

    await svc.notify_admins(text="t")

    assert [c for _, c, _ in bot.sent] == [2, 5]
    assert 7 in no_sleep


async def test_notify_users_retry_after_flood_keeps_the_photo(no_sleep):
    bot = FakeBot({10: [flood(3), None]})
    svc = AiogramNotificationService(bot=bot, admin_ids=[])

    await svc.notify_users(user_ids=[10], text="ad", photo_id="plate-photo")

    [(kind, chat, payload)] = bot.sent
    assert (kind, chat, payload["photo"]) == ("photo", 10, "plate-photo")


async def test_notify_users_continues_after_blocked_and_bad_users():
    bot = FakeBot({1: [forbidden()], 2: [bad_request()], 3: [RuntimeError()]})
    svc = AiogramNotificationService(bot=bot, admin_ids=[])

    await svc.notify_users(user_ids=[1, 2, 3, 4], text="t")

    assert [c for _, c, _ in bot.sent] == [4]


async def test_notify_user_handles_every_error_kind(no_sleep):
    for script in (
        [forbidden()],
        [bad_request()],
        [RuntimeError()],
        [flood(), forbidden()],
    ):
        bot = FakeBot({5: script})
        svc = AiogramNotificationService(bot=bot, admin_ids=[])
        await svc.notify_user(tg_id=5, text="t")  # не бросает
        assert bot.sent == []

    bot = FakeBot({5: [flood(2), None]})
    await AiogramNotificationService(bot=bot, admin_ids=[]).notify_user(
        tg_id=5, text="t"
    )
    assert [c for _, c, _ in bot.sent] == [5]


async def test_broadcast_copy_counts_outcomes(no_sleep):
    bot = FakeBot(
        {
            2: [forbidden()],
            3: [RuntimeError("x")],
            4: [flood(5), None],
            5: [flood(5), forbidden()],
            6: [flood(5), RuntimeError()],
        }
    )
    svc = AiogramNotificationService(bot=bot, admin_ids=[])

    result = await svc.broadcast_copy(
        chat_ids=[1, 2, 3, 4, 5, 6], from_chat_id=100, message_id=7
    )

    assert result == {"success": 2, "blocked": 2, "failed": 2, "fail": 4}
    assert [c for _, c, _ in bot.sent] == [1, 4]
