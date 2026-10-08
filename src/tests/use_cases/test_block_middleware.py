"""
Regression test for AUD-24: BlockCheckMiddleware's private-only enforcement
only resolved `chat` for Update.message / Update.callback_query.message.
Any other update type carrying its own chat (my_chat_member, chat_member,
chat_join_request) fell through with chat=None, silently skipping the
"only private chats" restriction for those update kinds.
"""

from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Chat, Update

from src.presentation.telegram.middlewares.block import BlockCheckMiddleware


def make_update(**chat_fields) -> Update:
    """A MagicMock(spec=Update) satisfies isinstance(event, Update) (aiogram's
    middleware dispatch relies on that) without needing to construct every
    required field of the real pydantic model."""
    update = MagicMock(spec=Update)
    update.message = None
    update.callback_query = None
    update.my_chat_member = None
    update.chat_member = None
    update.chat_join_request = None
    for field, chat in chat_fields.items():
        setattr(update, field, chat)
    return update


async def test_group_chat_via_my_chat_member_is_rejected():
    group_chat = MagicMock(spec=Chat)
    group_chat.type = "group"
    chat_member_update = MagicMock()
    chat_member_update.chat = group_chat

    update = make_update(my_chat_member=chat_member_update)
    middleware = BlockCheckMiddleware()
    handler = AsyncMock()
    data = {"event_from_user": MagicMock(id=1)}

    result = await middleware(handler, update, data)

    assert handler.await_count == 0
    assert result is None


async def test_group_chat_via_chat_member_is_rejected():
    group_chat = MagicMock(spec=Chat)
    group_chat.type = "supergroup"
    chat_member_update = MagicMock()
    chat_member_update.chat = group_chat

    update = make_update(chat_member=chat_member_update)
    middleware = BlockCheckMiddleware()
    handler = AsyncMock()
    data = {"event_from_user": MagicMock(id=1)}

    result = await middleware(handler, update, data)

    assert handler.await_count == 0
    assert result is None


async def test_private_chat_via_my_chat_member_is_allowed_through():
    private_chat = MagicMock(spec=Chat)
    private_chat.type = "private"
    chat_member_update = MagicMock()
    chat_member_update.chat = private_chat

    update = make_update(my_chat_member=chat_member_update)
    middleware = BlockCheckMiddleware()
    handler = AsyncMock(return_value="ok")

    container = MagicMock()

    async def fake_get(cls):
        cache = MagicMock()
        cache.get_flags = AsyncMock(return_value=(False, False))
        return cache

    container.get = fake_get
    data = {
        "event_from_user": MagicMock(id=1),
        "dishka_container": container,
    }

    result = await middleware(handler, update, data)

    assert handler.await_count == 1
    assert result == "ok"
