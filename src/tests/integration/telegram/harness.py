"""Симулятор Telegram для сквозных тестов бота.

Поднимается НАСТОЯЩИЙ бот: реальный Dispatcher со всеми роутерами и
диалогами, реальный dishka-контейнер, реальные use cases и SQLAlchemy-
репозитории на тестовом Postgres. Подменяется только «выход наружу»:

* HTTP-сессия aiogram -> ``FakeTelegramSession``: записывает каждый вызов
  Telegram Bot API и возвращает правдоподобный ответ; хранит сообщения,
  которые бот отправил/отредактировал, вместе с клавиатурами;
* Redis -> fakeredis (FSM-хранилище диалогов, холды слотов, кеш блокировок);
* очередь задач taskiq -> ``RecordingTaskQueue`` (видно, что и когда
  запланировано).

``TgUser`` отправляет боту апдейты так, как их прислал бы Telegram:
текст, команды, фото, нажатия inline-кнопок по их подписи.
"""

from __future__ import annotations

import asyncio
import itertools
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import (
    AnswerCallbackQuery,
    CopyMessage,
    DeleteMessage,
    EditMessageCaption,
    EditMessageMedia,
    EditMessageReplyMarkup,
    EditMessageText,
    GetChat,
    GetFile,
    GetChatMember,
    GetMe,
    SendMediaGroup,
    TelegramMethod,
)
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberMember,
    Contact,
    File,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageId,
    PhotoSize,
    ReplyKeyboardMarkup,
    SuccessfulPayment,
    Update,
    User,
)

BOT_ID = 4242


@dataclass
class SentMessage:
    """То, что видит пользователь в чате."""

    message: Message
    deleted: bool = False
    # Reply-клавиатура (кнопки под полем ввода) в Message не возвращается —
    # Telegram отдаёт только inline-разметку, поэтому храним её отдельно.
    reply_keyboard: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.message.text or self.message.caption or ""

    @property
    def buttons(self) -> list[InlineKeyboardButton]:
        markup = self.message.reply_markup
        if not isinstance(markup, InlineKeyboardMarkup):
            return []
        return [b for row in markup.inline_keyboard for b in row]

    @property
    def button_texts(self) -> list[str]:
        return [b.text for b in self.buttons]


class FakeTelegramSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []
        self.chats: dict[int, list[SentMessage]] = {}
        self.alerts: list[tuple[str | None, bool]] = []
        self._ids = itertools.count(10_000)

    def reset(self) -> None:
        self.calls.clear()
        self.chats.clear()
        self.alerts.clear()

    async def close(self) -> None:  # pragma: no cover - нечего закрывать
        pass

    async def stream_content(self, *a, **kw):
        """Скачивание файла по file_path — отдаём настоящий JPEG."""
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (64, 32), (200, 200, 200)).save(buf, format="JPEG")
        yield buf.getvalue()

    # --- helpers ---------------------------------------------------------

    def _find(self, chat_id: int, message_id: int) -> SentMessage | None:
        for sent in self.chats.get(chat_id, []):
            if sent.message.message_id == message_id:
                return sent
        return None

    def _photo(self, source: Any = None) -> list[PhotoSize]:
        """file_id отправленного фото: тот же, если слали по file_id
        (как в Telegram), иначе — новый, как после загрузки файла."""
        n = next(self._ids)
        file_id = source if isinstance(source, str) else f"photo-{n}"
        return [PhotoSize(file_id=file_id, file_unique_id=f"u{n}", width=1, height=1)]

    def _new_message(self, chat_id: int, **fields: Any) -> Message:
        markup = fields.get("reply_markup")
        reply_keyboard: list[str] = []
        if markup is not None and not isinstance(markup, InlineKeyboardMarkup):
            fields.pop("reply_markup")
            if isinstance(markup, ReplyKeyboardMarkup):
                reply_keyboard = [b.text for row in markup.keyboard for b in row]
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(timezone.utc),
            chat=Chat(id=chat_id, type="private" if chat_id > 0 else "channel"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
            **fields,
        )
        self.chats.setdefault(chat_id, []).append(
            SentMessage(message, reply_keyboard=reply_keyboard)
        )
        return message

    # --- BaseSession API -------------------------------------------------

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout=None):
        self.calls.append(method)
        _enforce_bot_api_limits(method)

        if isinstance(method, GetMe):
            return User(id=BOT_ID, is_bot=True, first_name="Bot", username="test_bot")
        if isinstance(method, GetChat):
            return Chat(id=int(method.chat_id), type="private")
        if isinstance(method, GetFile):
            return File(
                file_id=method.file_id,
                file_unique_id=method.file_id,
                file_path=f"photos/{method.file_id}.jpg",
            )
        if isinstance(method, GetChatMember):
            return ChatMemberMember(
                user=User(id=method.user_id, is_bot=False, first_name="U")
            )
        if isinstance(method, AnswerCallbackQuery):
            self.alerts.append((method.text, bool(method.show_alert)))
            return True
        if isinstance(method, DeleteMessage):
            sent = self._find(int(method.chat_id), method.message_id)
            if sent:
                sent.deleted = True
            return True
        if isinstance(
            method,
            (
                EditMessageText,
                EditMessageCaption,
                EditMessageMedia,
                EditMessageReplyMarkup,
            ),
        ):
            sent = self._find(int(method.chat_id), method.message_id)
            if sent is None:
                return True
            update: dict[str, Any] = {"edit_date": int(datetime.now().timestamp())}
            if isinstance(method, EditMessageText):
                update["text"] = method.text
            if isinstance(method, EditMessageCaption):
                update["caption"] = method.caption
            if isinstance(method, EditMessageMedia):
                update["photo"] = self._photo()
                update["caption"] = getattr(method.media, "caption", None)
                update["text"] = None
            update["reply_markup"] = (
                method.reply_markup
                if isinstance(method.reply_markup, InlineKeyboardMarkup)
                else None
            )
            sent.message = sent.message.model_copy(update=update)
            return sent.message
        if isinstance(method, CopyMessage):
            self._new_message(int(method.chat_id), text="<copy>")
            return MessageId(message_id=next(self._ids))
        if isinstance(method, SendMediaGroup):
            return [self._new_message(int(method.chat_id), photo=self._photo())]

        returning = getattr(method, "__returning__", None)
        if returning is Message:
            fields: dict[str, Any] = {}
            for name in ("text", "caption", "reply_markup"):
                value = getattr(method, name, None)
                if value is not None:
                    fields[name] = value
            if hasattr(method, "photo"):
                fields["photo"] = self._photo(method.photo)
            if hasattr(method, "title") and hasattr(method, "prices"):
                fields["text"] = f"<invoice {method.title}>"
            return self._new_message(int(method.chat_id), **fields)
        if returning is bool:
            return True
        if returning is str:  # createInvoiceLink и т.п.
            return f"https://t.me/$invoice-{next(self._ids)}"
        raise AssertionError(f"Симулятор не знает метод {type(method).__name__}")

    # --- запросы из тестов ----------------------------------------------

    def visible(self, chat_id: int) -> list[SentMessage]:
        return [m for m in self.chats.get(chat_id, []) if not m.deleted]

    def calls_of(self, method_type: type) -> list:
        return [c for c in self.calls if isinstance(c, method_type)]


_TAG_RE = re.compile(r"<[^>]+>")


def _visible_len(html_text: str | None) -> int:
    """Длина так, как её считает Telegram: после разбора HTML-разметки."""
    import html

    return len(html.unescape(_TAG_RE.sub("", html_text or "")))


def _enforce_bot_api_limits(method: TelegramMethod) -> None:
    """Те же ограничения, что у настоящего Bot API: без них сценарий мог
    бы пройти в тесте и упасть в проде с 400 Bad Request."""

    def bad(message: str) -> None:
        raise TelegramBadRequest(method=method, message=f"Bad Request: {message}")

    text = getattr(method, "text", None)
    if isinstance(method, AnswerCallbackQuery):
        if text and len(text) > 200:
            bad(f"MESSAGE_TOO_LONG (alert {len(text)} > 200)")
    elif isinstance(text, str) and _visible_len(text) > 4096:
        bad(f"message is too long ({_visible_len(text)} > 4096)")
    caption = getattr(method, "caption", None)
    if isinstance(caption, str) and _visible_len(caption) > 1024:
        bad(f"message caption is too long ({_visible_len(caption)} > 1024)")
    markup = getattr(method, "reply_markup", None)
    if isinstance(markup, InlineKeyboardMarkup):
        for row in markup.inline_keyboard:
            for button in row:
                data = button.callback_data
                if data is not None and len(data.encode()) > 64:
                    bad(f"BUTTON_DATA_INVALID ({data!r} > 64 bytes)")


class RecordingTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple]] = []
        self.scheduled: list[tuple[str, tuple, datetime, str]] = []
        self.canceled: list[str] = []
        self._ids = itertools.count(1)

    def reset(self) -> None:
        self.enqueued.clear()
        self.scheduled.clear()
        self.canceled.clear()

    async def enqueue(self, *, task_name: str, args: tuple) -> str:
        self.enqueued.append((task_name, args))
        return f"task-{next(self._ids)}"

    async def schedule(self, *, task_name: str, args: tuple, run_at_utc: datetime):
        job_id = f"job-{next(self._ids)}"
        self.scheduled.append((task_name, args, run_at_utc, job_id))
        return job_id

    async def cancel(self, *, job_id: str) -> bool:
        self.canceled.append(job_id)
        return True

    def names(self) -> list[str]:
        return [n for n, *_ in self.scheduled] + [n for n, _ in self.enqueued]


@dataclass
class TgUser:
    dp: Dispatcher
    bot: Bot
    tg: FakeTelegramSession
    id: int
    username: str | None = "tester"
    first_name: str = "Test"
    _update_ids: Any = field(default_factory=lambda: itertools.count(1))
    _msg_ids: Any = field(default_factory=lambda: itertools.count(1))

    @property
    def user(self) -> User:
        return User(
            id=self.id,
            is_bot=False,
            first_name=self.first_name,
            username=self.username,
        )

    @property
    def chat(self) -> Chat:
        return Chat(id=self.id, type="private")

    async def _feed(self, **update: Any) -> None:
        await self.dp.feed_update(
            self.bot, Update(update_id=next(self._update_ids), **update)
        )

    def _message(self, **fields: Any) -> Message:
        return Message(
            message_id=next(self._msg_ids),
            date=datetime.now(timezone.utc),
            chat=self.chat,
            from_user=self.user,
            **fields,
        )

    async def send(self, text: str) -> None:
        await self._feed(message=self._message(text=text))

    async def send_contact(self, phone: str) -> None:
        await self._feed(
            message=self._message(
                contact=Contact(
                    phone_number=phone, first_name=self.first_name, user_id=self.id
                )
            )
        )

    async def pay_stars(self, *, payload: str, stars: int) -> None:
        """Telegram присылает боту сообщение об успешной оплате инвойса."""
        await self._feed(
            message=self._message(
                successful_payment=SuccessfulPayment(
                    currency="XTR",
                    total_amount=stars,
                    invoice_payload=payload,
                    telegram_payment_charge_id="tg-charge",
                    provider_payment_charge_id="prov-charge",
                )
            )
        )

    async def send_photo(self, file_id: str = "user-photo") -> None:
        await self._feed(
            message=self._message(
                photo=[
                    PhotoSize(
                        file_id=file_id, file_unique_id=file_id, width=10, height=10
                    )
                ]
            )
        )

    # --- что видит пользователь -----------------------------------------

    @property
    def messages(self) -> list[SentMessage]:
        return self.tg.visible(self.id)

    @property
    def last(self) -> SentMessage:
        visible = self.messages
        assert visible, "бот ничего не отправил этому пользователю"
        return visible[-1]

    @property
    def last_alert(self) -> str | None:
        # aiogram-dialog после хендлера сам «пусто» отвечает на callback,
        # поэтому берём последний ответ с текстом
        texts = [text for text, _ in self.tg.alerts if text]
        return texts[-1] if texts else None

    def find_button(
        self, label: str | re.Pattern
    ) -> tuple[SentMessage, InlineKeyboardButton]:
        for sent in reversed(self.messages):
            for button in sent.buttons:
                if isinstance(label, re.Pattern):
                    ok = bool(label.search(button.text))
                else:
                    ok = label in button.text
                if ok:
                    return sent, button
        available = [b for m in self.messages for b in m.button_texts]
        raise AssertionError(f"Нет кнопки {label!r}. Доступны: {available}")

    async def click(self, label: str | re.Pattern) -> None:
        sent, button = self.find_button(label)
        assert button.callback_data, f"У кнопки {button.text!r} нет callback_data"
        await self._feed(
            callback_query=CallbackQuery(
                id=str(next(self._update_ids)),
                from_user=self.user,
                chat_instance="ci",
                message=sent.message,
                data=button.callback_data,
            )
        )


async def settle(rounds: int = 20) -> None:
    """Дождаться фоновых задач (BgManager aiogram-dialog запускает
    «телепорт» пользователя в диалог через asyncio.create_task)."""
    current = asyncio.current_task()
    for _ in range(rounds):
        pending = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
        if not pending:
            return
        await asyncio.wait(pending, timeout=0.5)


async def forge_click(u: "TgUser", widget_data: str) -> None:
    """Нажатие, которого нет на экране: модифицированный клиент Telegram
    может прислать любой callback_data для сообщения бота. Берём intent
    текущего диалога из видимой кнопки и подставляем свой widget/item."""
    sent = next(m for m in reversed(u.messages) if m.buttons)
    data = next(b.callback_data for b in sent.buttons if b.callback_data)
    intent = data.split("\x1d", 1)[0]
    await u._feed(
        callback_query=CallbackQuery(
            id=str(next(u._update_ids)),
            from_user=u.user,
            chat_instance="ci",
            message=sent.message,
            data=f"{intent}\x1d{widget_data}",
        )
    )


async def forge_raw_callback(u: "TgUser", data: str) -> None:
    """Callback с произвольными данными (не диалоговый) на сообщение бота."""
    sent = u.last
    await u._feed(
        callback_query=CallbackQuery(
            id=str(next(u._update_ids)),
            from_user=u.user,
            chat_instance="ci",
            message=sent.message,
            data=data,
        )
    )
