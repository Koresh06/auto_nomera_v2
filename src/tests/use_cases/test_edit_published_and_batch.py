"""
Coverage for EditPublishedAdUseCase, PublishOverdueBatchUseCase, and a direct
test of ConfirmPaidSlotAndSchedulePublicationUseCase — previously untested.
"""

from datetime import timedelta

import pytest

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.use_cases.publication.confirm_paid_slot_and_schedule_publication import (
    ConfirmPaidSlotAndSchedulePublicationRequest,
    ConfirmPaidSlotAndSchedulePublicationUseCase,
)
from src.application.use_cases.publication.edit_published import (
    EditPublishedAdRequest,
    EditPublishedAdUseCase,
)
from src.application.use_cases.publication.publish_overdue_batch import (
    PublishOverdueBatchRequest,
    PublishOverdueBatchUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.scheduler.taskiq_queue_scheduler import TaskQueueScheduler


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}
        self.saved: list[Ad] = []

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)

    async def save(self, ad: Ad) -> None:
        self.saved.append(ad)


class FakePublicationRepo:
    def __init__(self, pubs: list[Publication] | None = None) -> None:
        self._store = {p.id: p for p in (pubs or [])}

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeTelegramPublisher:
    def __init__(self) -> None:
        self.edits: list[tuple] = []

    async def edit_caption(
        self, *, channel_id: int, message_id: int, caption: str
    ) -> None:
        self.edits.append((channel_id, message_id, caption))


class FakeTaskQueue:
    async def schedule(self, *, task_name: str, args, run_at_utc) -> str | None:
        return "job-id"

    async def enqueue(self, *, task_name: str, args) -> str | None:
        return "job-id"

    async def cancel(self, *, job_id: str) -> bool:
        return True


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_region() -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


def make_ad_with_content(**overrides) -> Ad:
    defaults = dict(
        id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.PUBLISHED
    )
    defaults.update(overrides)
    ad = Ad(**defaults)
    ad.fill_content(
        AdContent(
            plate_number="А001АА77",
            city="OldCity",
            price=Price(100_000),
            contacts=Contacts(username="seller"),
        )
    )
    return ad


# ---------- EditPublishedAdUseCase ----------


async def test_edit_published_ad_updates_content_and_edits_caption():
    ad = make_ad_with_content()
    pub = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.PUBLISHED,
        channel_message_id=999,
    )
    telegram = FakeTelegramPublisher()
    use_case = EditPublishedAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([pub]),
        region_repo=FakeRegionRepo(make_region()),
        telegram=telegram,
        renderer=AdTextRenderer(
            bot_url="https://t.me/bot", buyout_url="https://t.me/buyout"
        ),
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(EditPublishedAdRequest(ad_id=1, publication_id=1, city="NewCity"))

    assert ad.content.city == "NewCity"
    assert len(telegram.edits) == 1
    channel_id, message_id, caption = telegram.edits[0]
    assert message_id == 999
    assert "NewCity" in caption


async def test_edit_published_ad_rejects_non_published():
    ad = make_ad_with_content()
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    use_case = EditPublishedAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([pub]),
        region_repo=FakeRegionRepo(make_region()),
        telegram=FakeTelegramPublisher(),
        renderer=AdTextRenderer(bot_url="x", buyout_url="y"),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(InvalidPublicationState):
        await use_case(EditPublishedAdRequest(ad_id=1, publication_id=1))


async def test_edit_published_ad_rejects_missing_message_id():
    ad = make_ad_with_content()
    pub = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.PUBLISHED,
        channel_message_id=None,
    )
    use_case = EditPublishedAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([pub]),
        region_repo=FakeRegionRepo(make_region()),
        telegram=FakeTelegramPublisher(),
        renderer=AdTextRenderer(bot_url="x", buyout_url="y"),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(EditPublishedAdRequest(ad_id=1, publication_id=1))


async def test_edit_published_ad_unknown_ad_raises():
    use_case = EditPublishedAdUseCase(
        ad_repo=FakeAdRepo([]),
        publication_repo=FakePublicationRepo([]),
        region_repo=FakeRegionRepo(make_region()),
        telegram=FakeTelegramPublisher(),
        renderer=AdTextRenderer(bot_url="x", buyout_url="y"),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(AdNotFoundException):
        await use_case(EditPublishedAdRequest(ad_id=1, publication_id=1))


async def test_edit_published_ad_unknown_publication_raises():
    ad = make_ad_with_content()
    use_case = EditPublishedAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([]),
        region_repo=FakeRegionRepo(make_region()),
        telegram=FakeTelegramPublisher(),
        renderer=AdTextRenderer(bot_url="x", buyout_url="y"),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(PublicationNotFoundException):
        await use_case(EditPublishedAdRequest(ad_id=1, publication_id=1))


# ---------- PublishOverdueBatchUseCase ----------


class FakePublishPublication:
    def __init__(self, fail_ids: set[int] | None = None) -> None:
        self._fail_ids = fail_ids or set()
        self.calls: list[int] = []

    async def __call__(self, command) -> None:
        self.calls.append(command.publication_id)
        if command.publication_id in self._fail_ids:
            raise RuntimeError("boom")


async def test_publish_overdue_batch_counts_success_and_failure():
    publish = FakePublishPublication(fail_ids={2})
    use_case = PublishOverdueBatchUseCase(publish_publication=publish)

    result = await use_case(PublishOverdueBatchRequest(publication_ids=[1, 2, 3]))

    assert result.success == 2
    assert result.failed == [2]
    assert publish.calls == [1, 2, 3]  # one failure doesn't stop the batch


async def test_publish_overdue_batch_all_succeed():
    publish = FakePublishPublication()
    use_case = PublishOverdueBatchUseCase(publish_publication=publish)

    result = await use_case(PublishOverdueBatchRequest(publication_ids=[1, 2]))

    assert result.success == 2
    assert result.failed == []


# ---------- ConfirmPaidSlotAndSchedulePublicationUseCase ----------


async def test_confirm_paid_slot_and_schedule_publication_requires_slot_set():
    pub = Publication(
        id=1, ad_id=1, region_id=1, status=PublicationStatus.AWAITING_PAYMENT
    )
    use_case = ConfirmPaidSlotAndSchedulePublicationUseCase(
        publication_repo=FakePublicationRepo([pub]),
        scheduler=TaskQueueScheduler(
            queue=FakeTaskQueue(),
            publication_repo=FakePublicationRepo([pub]),
            transaction_manager=FakeTransactionManager(),
        ),
        reservation_service=_make_reservation_service(),
        task_queue=FakeTaskQueue(),
        settings=_FakeSettings(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(
            ConfirmPaidSlotAndSchedulePublicationRequest(
                publication_id=1, user_id=1, ad_id=1
            )
        )


async def test_confirm_paid_slot_and_schedule_publication_rejects_wrong_status():
    import datetime as dt

    slot = SlotKey(
        region_id=1, local_day=dt.date(2026, 2, 12), local_time=dt.time(10, 0)
    )
    pub = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.PUBLISHED,
        slot=slot,
        publish_at_utc=dt.datetime(2026, 2, 12, 7, 0, tzinfo=dt.timezone.utc),
    )
    pub_repo = FakePublicationRepo([pub])
    use_case = ConfirmPaidSlotAndSchedulePublicationUseCase(
        publication_repo=pub_repo,
        scheduler=TaskQueueScheduler(
            queue=FakeTaskQueue(),
            publication_repo=pub_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        reservation_service=_make_reservation_service(),
        task_queue=FakeTaskQueue(),
        settings=_FakeSettings(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(InvalidPublicationState):
        await use_case(
            ConfirmPaidSlotAndSchedulePublicationRequest(
                publication_id=1, user_id=1, ad_id=1
            )
        )


async def test_confirm_paid_slot_and_schedule_publication_schedules_successfully():
    import datetime as dt

    slot = SlotKey(
        region_id=1, local_day=dt.date(2026, 2, 12), local_time=dt.time(10, 0)
    )
    pub = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.AWAITING_PAYMENT,
        slot=slot,
        publish_at_utc=dt.datetime(2026, 2, 12, 7, 0, tzinfo=dt.timezone.utc),
    )
    pub_repo = FakePublicationRepo([pub])
    use_case = ConfirmPaidSlotAndSchedulePublicationUseCase(
        publication_repo=pub_repo,
        scheduler=TaskQueueScheduler(
            queue=FakeTaskQueue(),
            publication_repo=pub_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        reservation_service=_make_reservation_service(),
        task_queue=FakeTaskQueue(),
        settings=_FakeSettings(),
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(
        ConfirmPaidSlotAndSchedulePublicationRequest(
            publication_id=1, user_id=1, ad_id=1
        )
    )

    final = await pub_repo.get_by_id(1)
    assert final.status == PublicationStatus.SCHEDULED
    assert final.scheduler_job_id is not None


def _make_reservation_service():
    from src.domain.services.slots.slot_reservation_service import (
        SlotReservationService,
    )
    from src.infrastructure.redis.holt_store.in_memory import InMemorySlotHoldStore
    from src.infrastructure.repositories.slot.in_memory import (
        InMemorySlotBookingRepo,
        InMemorySlotConvertedRepo,
    )

    return SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        hold_ttl=timedelta(minutes=15),
    )


class _FakeSettings:
    class _App:
        debug = True
        pre_publication_window_hours = 2

    app = _App()
