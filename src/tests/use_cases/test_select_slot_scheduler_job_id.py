"""
Regression test: scheduler_job_id must not be overwritten by notify_scheduled save().

Bug scenario:
  1. publication entity A is loaded (scheduler_job_id=None)
  2. schedule_publication() creates entity B internally, sets scheduler_job_id=job_id,
     saves B and commits — session expires all ORM objects
  3. _schedule_pre_publication_notification() saves entity A (scheduler_job_id still None)
     → save() does a full overwrite, resetting scheduler_job_id back to NULL in DB

Fix: reload publication after schedule_publication() so entity A has fresh scheduler_job_id.
"""

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import MagicMock


from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationRequest,
    SelectSlotForPublicationUseCase,
)
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.publication import PublicationStatus
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.scheduler.taskiq_queue_scheduler import TaskQueueScheduler

FAKE_JOB_ID = "taskiq-job-abc123"


class FakePublicationRepo:
    """Mimics the real SQLAlchemy repo's full-overwrite save() behavior."""

    def __init__(self) -> None:
        self._store: dict[int, dict] = {}

    def seed(self, pub: Publication) -> None:
        self._snapshot(pub)

    def _snapshot(self, pub: Publication) -> None:
        self._store[pub.id] = dict(
            id=pub.id,
            ad_id=pub.ad_id,
            region_id=pub.region_id,
            status=pub.status,
            slot=pub.slot,
            publish_at_utc=pub.publish_at_utc,
            scheduler_job_id=pub.scheduler_job_id,
            channel_message_id=pub.channel_message_id,
            published_at_utc=pub.published_at_utc,
            is_child=pub.is_child,
            notify_scheduled=pub.notify_scheduled,
            services=list(pub.services),
        )

    async def get_by_id(self, publication_id: int) -> Publication | None:
        data = self._store.get(publication_id)
        if data is None:
            return None
        # Return a new Python object, just like the real repo's to_entity() does.
        return Publication(**dict(data))

    async def save(self, publication: Publication) -> None:
        # Full overwrite: copies ALL fields from the entity (simulates _update_model).
        # This is what causes scheduler_job_id to be reset to None when a stale
        # entity is passed after schedule_publication has already set it.
        self._snapshot(publication)


class FakeTransactionManager:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


class FakeTaskQueue:
    async def schedule(self, *, task_name: str, args, run_at_utc) -> str | None:
        if task_name == "publish_publication":
            return FAKE_JOB_ID
        return None

    async def enqueue(self, *, task_name: str, args) -> None:
        pass

    async def cancel(self, *, job_id: str) -> None:
        pass


class FakeRegionRepo:
    def __init__(self, region: Region) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        return self._region if self._region.id == region_id else None


class FakeSlotConvertedRepo:
    async def get_converted_owner_and_ad(self, slot: SlotKey):
        return None  # free slot, not converted

    async def mark_converted(self, slot: SlotKey, *, user_id: int, ad_id=None) -> bool:
        return True


class FakeSlotBookingRepo:
    async def is_booked(self, slot: SlotKey) -> bool:
        return False

    async def book(self, slot: SlotKey, *, ad_id=None, user_id: int) -> bool:
        return True

    async def get_booking_owner(self, slot: SlotKey) -> int | None:
        return None


class FakeSlotHoldStore:
    async def get(self, slot: SlotKey):
        return None

    async def set(self, slot: SlotKey, owner, ttl) -> None:
        pass

    async def delete(self, slot: SlotKey) -> None:
        pass


async def test_scheduler_job_id_not_overwritten_by_notify_scheduled_save() -> None:
    """
    After schedule_publication commits (writing scheduler_job_id), a subsequent
    save() of the stale publication entity must not reset scheduler_job_id to None.
    Both scheduler_job_id and notify_scheduled must be persisted after the use case.
    """
    region_id = 1
    pub_id = 1
    ad_id = 42
    user_id = 100

    pub_repo = FakePublicationRepo()
    pub_repo.seed(
        Publication(
            id=pub_id, ad_id=ad_id, region_id=region_id, status=PublicationStatus.DRAFT
        )
    )

    fake_queue = FakeTaskQueue()
    fake_tx = FakeTransactionManager()

    scheduler = TaskQueueScheduler(
        queue=fake_queue,
        publication_repo=pub_repo,
        transaction_manager=fake_tx,
    )

    region = Region(
        id=region_id,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-1001234567,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        # system_paid_slots_count=0: этот тест проверяет персистентность
        # scheduler_job_id, а не прайсинг слотов. С count>0 тест был
        # чувствителен к времени суток запуска (today 10:00 мог попасть в
        # "первые N платных" слотов региона и уйти в ветку AWAITING_PAYMENT,
        # вообще не вызывая schedule_publication). pricing теперь берётся из
        # region.settings внутри use case (см. AUD-10), а не из отдельного
        # DI-параметра, поэтому настраиваем это здесь.
        settings=RegionSettings(system_paid_slots_count=0),
    )

    reservation_service = SlotReservationService(
        booking_repo=FakeSlotBookingRepo(),
        converted_repo=FakeSlotConvertedRepo(),
        hold_store=FakeSlotHoldStore(),
        hold_ttl=timedelta(minutes=5),
    )

    settings = MagicMock()
    settings.app.debug = (
        True  # publish_at_utc = now+2m, notify_at = now+1m → branch taken
    )
    settings.app.pre_publication_window_hours = 2

    use_case = SelectSlotForPublicationUseCase(
        publication_repo=pub_repo,
        region_repo=FakeRegionRepo(region),
        scheduler=scheduler,
        calendar_builder=CalendarBuilder(),
        time_resolver=PublishTimeResolver(),
        reservation_service=reservation_service,
        task_queue=fake_queue,
        settings=settings,
        transaction_manager=fake_tx,
    )

    now = datetime.now(timezone.utc)
    slot = SlotKey(
        region_id=region_id,
        local_day=date.today(),
        local_time=time(10, 0),
    )

    await use_case(
        SelectSlotForPublicationRequest(
            publication_id=pub_id,
            slot=slot,
            user_id=user_id,
            ad_id=ad_id,
            now_utc=now,
            payment_confirmed=False,
        )
    )

    final = await pub_repo.get_by_id(pub_id)
    assert final is not None
    assert final.scheduler_job_id == FAKE_JOB_ID, (
        f"scheduler_job_id was overwritten. Got: {final.scheduler_job_id!r}. "
        "The stale entity's save() in _schedule_pre_publication_notification "
        "reset scheduler_job_id to None."
    )
    assert final.notify_scheduled is True, (
        f"notify_scheduled was not persisted. Got: {final.notify_scheduled!r}"
    )
