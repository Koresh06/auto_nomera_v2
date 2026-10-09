"""Контракт «продюсер -> taskiq -> воркер» на настоящем taskiq-брокере.

Код ставит задачи по строковому имени (``task_name="publish_publication"``),
а ``TaskiqTaskQueue`` ищет их в реестре брокера. Опечатка в имени или
несовпадение аргументов с сигнатурой задачи в проде проявились бы только
в рантайме воркера — здесь это ловится тестом."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import fakeredis
import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from redis.asyncio import Redis
from taskiq import InMemoryBroker

from src.application.mediator import Mediator
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.miling.execute import ExecuteMailingRequest
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersRequest,
)
from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.application.use_cases.payment.mark import MarkPaymentFailedRequest
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)
from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
)
from src.domain.enums.miling import MailingType
from src.infrastructure.broker.taskiq import register_taskiq_tasks
from src.infrastructure.tasks.taskiq_queue import TaskiqTaskQueue


class RecordingMediator:
    def __init__(self) -> None:
        self.handled: list = []

    async def handle(self, request):
        self.handled.append(request)


class FakeNotifications:
    def __init__(self, broadcast_result=None, notify_user_exc=None) -> None:
        self.broadcast_calls: list = []
        self.admin_texts: list[str] = []
        self.user_calls: list = []
        self._result = broadcast_result or {"success": 1, "blocked": 0, "failed": 0}
        self._exc = notify_user_exc

    async def broadcast_copy(self, *, chat_ids, from_chat_id, message_id):
        self.broadcast_calls.append((chat_ids, from_chat_id, message_id))
        return dict(self._result)

    async def notify_admins(self, *, text, **kw):
        self.admin_texts.append(text)

    async def notify_user(self, *, tg_id, text, **kw):
        self.user_calls.append(tg_id)
        if self._exc:
            raise self._exc


class FakeContainer:
    """Повторяет форму dishka-контейнера, как его использует broker/taskiq.py."""

    def __init__(self, deps: dict) -> None:
        self._deps = deps

    @asynccontextmanager
    async def _scope(self):
        yield self

    def __call__(self):
        return self._scope()

    async def get(self, key):
        return self._deps[key]


class FakeScheduleSource:
    def __init__(self, fail_delete: bool = False) -> None:
        self.added: list = []
        self.deleted: list[str] = []
        self._fail = fail_delete

    async def add_schedule(self, schedule) -> None:
        self.added.append(schedule)

    async def delete_schedule(self, schedule_id: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self.deleted.append(schedule_id)


@pytest.fixture
def env():
    broker = InMemoryBroker(await_inplace=True)
    mediator = RecordingMediator()
    notifications = FakeNotifications()
    redis = fakeredis.FakeAsyncRedis()
    container = FakeContainer(
        {Mediator: mediator, NotificationService: notifications, Redis: redis}
    )
    register_taskiq_tasks(broker, container=container)
    source = FakeScheduleSource()
    queue = TaskiqTaskQueue(broker, source)
    return queue, mediator, notifications, redis, source


@pytest.mark.parametrize(
    "task_name,args,expected",
    [
        ("publish_publication", (7,), PublishPublicationRequest(publication_id=7)),
        (
            "unpin_message",
            (-100, 55),
            UnpinMessageRequest(channel_id=-100, message_id=55),
        ),
        (
            "notify_pre_publication_users",
            (3,),
            NotifyPrePublicationUsersRequest(ad_id=3),
        ),
        ("confirm_payment", ("ext-1",), ConfirmPaymentRequest(external_id="ext-1")),
        (
            "mark_payment_failed",
            ("ext-2",),
            MarkPaymentFailedRequest(external_id="ext-2"),
        ),
        (
            "execute_mailing",
            (MailingType.TO_REGION.value, 1, 2, 9),
            ExecuteMailingRequest(
                mail_type=MailingType.TO_REGION,
                from_chat_id=1,
                message_id=2,
                region_id=9,
            ),
        ),
    ],
)
async def test_enqueued_task_reaches_use_case_with_same_args(
    env, task_name, args, expected
):
    queue, mediator, *_ = env

    job_id = await queue.enqueue(task_name=task_name, args=args)

    assert job_id
    [got] = mediator.handled
    assert type(got) is type(expected)
    assert vars(got) == vars(expected)


def test_every_task_name_used_by_producers_is_registered(env):
    """Все имена задач, которые встречаются в коде как ``task_name="..."``,
    находятся в реестре брокера."""
    import pathlib
    import re

    queue, *_ = env
    root = pathlib.Path(__file__).resolve().parents[2]
    names = set()
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        names |= set(re.findall(r'task_name="([a-z_]+)"', path.read_text()))

    assert names, "не найдено ни одного продюсера задач"
    for name in sorted(names):
        assert queue._get_task(name) is not None, name


async def test_unknown_task_name_fails_loudly(env):
    queue, *_ = env
    with pytest.raises(RuntimeError):
        await queue.enqueue(task_name="no_such_task", args=())


async def test_schedule_registers_by_time_with_returned_id(env):
    queue, _, _, _, source = env
    run_at = datetime.now(timezone.utc) + timedelta(hours=1)

    job_id = await queue.schedule(
        task_name="publish_publication", args=(11,), run_at_utc=run_at
    )

    [scheduled] = source.added
    assert scheduled.schedule_id == job_id
    assert scheduled.time == run_at
    assert list(scheduled.args) == [11]
    assert scheduled.task_name.endswith("publish_publication")


async def test_cancel_reports_success_and_failure(env):
    queue, _, _, _, source = env
    assert await queue.cancel(job_id="j1") is True
    assert source.deleted == ["j1"]

    failing = TaskiqTaskQueue(queue._broker, FakeScheduleSource(fail_delete=True))
    assert await failing.cancel(job_id="j2") is False


async def test_mailing_batches_aggregate_and_report_once(env):
    queue, _, notifications, redis, _ = env
    notifications._result = {"success": 2, "blocked": 1, "failed": 0}

    for idx in (1, 2):
        await queue.enqueue(
            task_name="execute_mailing_batch",
            args=([1, 2, 3], 10, 20, idx, 2, "Всем", "mid-1"),
        )

    assert len(notifications.broadcast_calls) == 2
    assert len(notifications.admin_texts) == 1
    report = notifications.admin_texts[0]
    assert "Доставлено: <b>4</b>" in report
    assert "Заблокировали бота: <b>2</b>" in report
    assert "Всего: <b>6</b>" in report
    # счётчики рассылки подчищены
    assert await redis.exists("mailing_result:mid-1") == 0


async def test_mailing_batch_does_not_report_before_last_batch(env):
    queue, _, notifications, redis, _ = env
    await queue.enqueue(
        task_name="execute_mailing_batch",
        args=([1], 10, 20, 1, 3, "Всем", "mid-2"),
    )
    assert notifications.admin_texts == []
    assert int(await redis.hget("mailing_result:mid-2", "done_batches")) == 1


async def test_draft_reminder_swallows_blocked_bot(env):
    queue, _, notifications, *_ = env
    notifications._exc = TelegramForbiddenError(
        method=SendMessage(chat_id=1, text="x"), message="blocked"
    )

    await queue.enqueue(task_name="send_ad_draft_reminder", args=(42,))

    assert notifications.user_calls == [42]


async def test_draft_reminder_swallows_unexpected_errors(env):
    queue, _, notifications, *_ = env
    notifications._exc = RuntimeError("boom")

    await queue.enqueue(task_name="send_ad_draft_reminder", args=(43,))

    assert notifications.user_calls == [43]
