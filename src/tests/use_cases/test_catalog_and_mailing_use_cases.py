"""
Coverage for GetCatalogDeferredPublicationsUseCase (catalog/) and
EnqueueMailingUseCase / ExecuteMailingUseCase (miling/) — previously
entirely untested.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock


from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    GetCatalogDeferredPublicationsRequest,
    GetCatalogDeferredPublicationsUseCase,
)
from src.application.use_cases.miling import execute as execute_module
from src.application.use_cases.miling.enqueue import (
    EnqueueMailingRequest,
    EnqueueMailingUseCase,
)
from src.application.use_cases.miling.execute import (
    ExecuteMailingRequest,
    ExecuteMailingUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.miling import MailingType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}
        self.urgent_result: list[Ad] = []

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)

    async def list_urgent_published(self, region_id: int) -> list[Ad]:
        return self.urgent_result


class FakePublicationRepo:
    def __init__(self) -> None:
        self.pre_publication_result: list[Publication] = []

    async def list_pre_publication(self, region_id, now_utc, before_utc):
        return self.pre_publication_result


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None

    async def get_all(self) -> list[Region]:
        return [self._region] if self._region else []


class FakeTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple]] = []

    async def enqueue(self, *, task_name: str, args) -> str | None:
        self.enqueued.append((task_name, args))
        return "job-id"


class FakeUserRepo:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = users or []

    async def get_all(self) -> list[User]:
        return self._users

    async def get_by_region(self, region_id: int) -> list[User]:
        return [u for u in self._users if u.region_id == region_id]


class FakeNotificationService:
    def __init__(self) -> None:
        self.admin_notifications: list[str] = []

    async def notify_admins(
        self, *, text: str, photo_id=None, reply_markup=None
    ) -> None:
        self.admin_notifications.append(text)


def make_region(status: RegionStatus = RegionStatus.ACTIVE, **overrides) -> Region:
    defaults = dict(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=status,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )
    defaults.update(overrides)
    return Region(**defaults)


def make_user(**overrides) -> User:
    defaults = dict(
        id=1, tg_id=1001, role=UserRole.USER, phone=None, region_id=1, balance=0
    )
    defaults.update(overrides)
    return User(**defaults)


# ---------- GetCatalogDeferredPublicationsUseCase ----------


async def test_get_catalog_merges_urgent_and_pre_publication_sorted_by_created_at():
    region = make_region()
    old_ad = Ad(
        id=1,
        user_id=1,
        region_id=1,
        ad_type=AdType.URGENT_BUYOUT,
        status=AdStatus.PUBLISHED,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    new_ad = Ad(
        id=2,
        user_id=1,
        region_id=1,
        ad_type=AdType.SALE,
        status=AdStatus.READY,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    pub = Publication(id=1, ad_id=2, region_id=1, status=PublicationStatus.SCHEDULED)

    ad_repo = FakeAdRepo([old_ad, new_ad])
    ad_repo.urgent_result = [old_ad]
    pub_repo = FakePublicationRepo()
    pub_repo.pre_publication_result = [pub]

    settings = MagicMock()
    settings.app.debug = True

    use_case = GetCatalogDeferredPublicationsUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=ad_repo,
        publication_repo=pub_repo,
        settings=settings,
    )

    result = await use_case(GetCatalogDeferredPublicationsRequest(region_id=1))

    assert len(result) == 2
    # newest first
    assert result[0].ad.id == 2
    assert result[0].is_urgent is False
    assert result[1].ad.id == 1
    assert result[1].is_urgent is True


async def test_get_catalog_skips_pre_publication_with_missing_ad():
    region = make_region()
    pub = Publication(id=1, ad_id=999, region_id=1, status=PublicationStatus.SCHEDULED)
    ad_repo = FakeAdRepo([])  # ad 999 doesn't exist
    pub_repo = FakePublicationRepo()
    pub_repo.pre_publication_result = [pub]

    settings = MagicMock()
    settings.app.debug = True

    use_case = GetCatalogDeferredPublicationsUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=ad_repo,
        publication_repo=pub_repo,
        settings=settings,
    )

    result = await use_case(GetCatalogDeferredPublicationsRequest(region_id=1))

    assert result == []


# ---------- EnqueueMailingUseCase ----------


async def test_enqueue_mailing_enqueues_execute_task():
    queue = FakeTaskQueue()
    use_case = EnqueueMailingUseCase(task_queue=queue)

    await use_case(
        EnqueueMailingRequest(
            mail_type=MailingType.TO_REGION,
            from_chat_id=555,
            message_id=10,
            region_id=2,
        )
    )

    assert queue.enqueued == [("execute_mailing", ("region", 555, 10, 2))]


# ---------- ExecuteMailingUseCase ----------


async def test_execute_mailing_to_region_filters_blocked_users():
    users = [
        make_user(id=1, tg_id=1, region_id=2, is_blocked=False),
        make_user(id=2, tg_id=2, region_id=2, is_blocked=True),
        make_user(id=3, tg_id=3, region_id=3, is_blocked=False),  # different region
    ]
    queue = FakeTaskQueue()
    use_case = ExecuteMailingUseCase(
        user_repo=FakeUserRepo(users),
        region_repo=FakeRegionRepo(None),
        notification_service=FakeNotificationService(),
        task_queue=queue,
    )

    await use_case(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_REGION,
            from_chat_id=555,
            message_id=10,
            region_id=2,
        )
    )

    assert len(queue.enqueued) == 1
    task_name, args = queue.enqueued[0]
    assert task_name == "execute_mailing_batch"
    batch = args[0]
    assert batch == [1]  # only the non-blocked user in region 2


async def test_execute_mailing_to_region_requires_region_id():
    use_case = ExecuteMailingUseCase(
        user_repo=FakeUserRepo([]),
        region_repo=FakeRegionRepo(None),
        notification_service=FakeNotificationService(),
        task_queue=FakeTaskQueue(),
    )

    # the use case catches its own exceptions and notifies admins instead of raising
    notifier = FakeNotificationService()
    use_case.notification_service = notifier

    await use_case(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_REGION,
            from_chat_id=555,
            message_id=10,
            region_id=None,
        )
    )

    assert len(notifier.admin_notifications) == 1
    assert "Ошибка рассылки" in notifier.admin_notifications[0]


async def test_execute_mailing_to_all_regions_uses_channel_ids():
    region = make_region(channel_id=-100999)
    use_case = ExecuteMailingUseCase(
        user_repo=FakeUserRepo([]),
        region_repo=FakeRegionRepo(region),
        notification_service=FakeNotificationService(),
        task_queue=(queue := FakeTaskQueue()),
    )

    await use_case(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_ALL_REGIONS, from_chat_id=555, message_id=10
        )
    )

    assert len(queue.enqueued) == 1
    assert queue.enqueued[0][1][0] == [-100999]


async def test_execute_mailing_no_recipients_does_not_enqueue():
    use_case = ExecuteMailingUseCase(
        user_repo=FakeUserRepo([]),
        region_repo=FakeRegionRepo(None),
        notification_service=FakeNotificationService(),
        task_queue=(queue := FakeTaskQueue()),
    )

    await use_case(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_ALL, from_chat_id=555, message_id=10
        )
    )

    assert queue.enqueued == []


async def test_execute_mailing_splits_into_batches(monkeypatch):
    monkeypatch.setattr(execute_module, "BATCH_SIZE", 2)
    users = [make_user(id=i, tg_id=i, region_id=1) for i in range(1, 6)]  # 5 users
    use_case = ExecuteMailingUseCase(
        user_repo=FakeUserRepo(users),
        region_repo=FakeRegionRepo(None),
        notification_service=FakeNotificationService(),
        task_queue=(queue := FakeTaskQueue()),
    )

    await use_case(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_ALL, from_chat_id=555, message_id=10
        )
    )

    assert len(queue.enqueued) == 3  # 5 users / batch size 2 -> 3 batches
    total_batches_seen = {args[4] for _, args in queue.enqueued}
    assert total_batches_seen == {3}
