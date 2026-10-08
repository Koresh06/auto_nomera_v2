"""
Regression test for AUD-10: SelectSlotForPublicationUseCase used to build its
pricing decision from a globally-injected SlotPricingPolicy(system_paid_count=3)
instead of region.settings.system_paid_slots_count. A region configured with
a non-default value (e.g. 1 free slot instead of 3) would get the wrong
pricing decision at confirmation time, diverging from what hold_slot/the
calendar preview already correctly computed from the region's own settings.
"""

from datetime import datetime, timedelta, timezone
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


class FakePublicationRepo:
    def __init__(self, pub: Publication) -> None:
        self._store: dict[int, Publication] = {pub.id: pub}

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


class FakeTaskQueue:
    async def schedule(self, *, task_name: str, args, run_at_utc) -> str | None:
        return "job-id"

    async def enqueue(self, *, task_name: str, args) -> str | None:
        return "job-id"

    async def cancel(self, *, job_id: str) -> bool:
        return True


class FakeRegionRepo:
    def __init__(self, region: Region) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        return self._region if self._region.id == region_id else None


class FakeSlotConvertedRepo:
    async def get_converted_owner_and_ad(self, slot: SlotKey):
        return None

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

    async def set(self, slot: SlotKey, owner, ttl) -> bool:
        return True

    async def delete(self, slot: SlotKey) -> None:
        pass


def make_region(system_paid_slots_count: int) -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-1001234567,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        settings=RegionSettings(system_paid_slots_count=system_paid_slots_count),
    )


def make_use_case(
    region: Region, pub_repo: FakePublicationRepo
) -> SelectSlotForPublicationUseCase:
    fake_queue = FakeTaskQueue()
    fake_tx = FakeTransactionManager()
    scheduler = TaskQueueScheduler(
        queue=fake_queue, publication_repo=pub_repo, transaction_manager=fake_tx
    )
    reservation_service = SlotReservationService(
        booking_repo=FakeSlotBookingRepo(),
        converted_repo=FakeSlotConvertedRepo(),
        hold_store=FakeSlotHoldStore(),
        hold_ttl=timedelta(minutes=5),
    )
    settings = MagicMock()
    settings.app.debug = True
    settings.app.pre_publication_window_hours = 2

    return SelectSlotForPublicationUseCase(
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


async def test_second_future_slot_is_paid_when_region_allows_three():
    """system_paid_slots_count=3 means the 3 *soonest* chronological slots
    are the region's paid "premium" slots (SlotPricing.SYSTEM — "первые N
    слотов по политике региона"). The 2nd future slot (index 1) falls inside
    that window, so it must require payment."""
    region = make_region(system_paid_slots_count=3)
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.DRAFT)
    pub_repo = FakePublicationRepo(pub)
    use_case = make_use_case(region, pub_repo)

    now = datetime.now(timezone.utc)
    future = CalendarBuilder().generate_future_slots(region=region, now_utc=now)
    second_slot = future[1]

    await use_case(
        SelectSlotForPublicationRequest(
            publication_id=1,
            slot=second_slot,
            user_id=100,
            ad_id=1,
            now_utc=now,
            payment_confirmed=False,
        )
    )

    final = await pub_repo.get_by_id(1)
    assert final.status == PublicationStatus.AWAITING_PAYMENT


async def test_second_future_slot_is_free_when_region_allows_only_one():
    """AUD-10: with system_paid_slots_count=1 (a per-region override), only
    the very first chronological slot is the region's paid "premium" slot —
    the 2nd slot falls outside that window and must be free. This must come
    from the region's own settings, not a hardcoded global default of 3
    (which would have wrongly put the 2nd slot inside the paid window too)."""
    region = make_region(system_paid_slots_count=1)
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.DRAFT)
    pub_repo = FakePublicationRepo(pub)
    use_case = make_use_case(region, pub_repo)

    now = datetime.now(timezone.utc)
    future = CalendarBuilder().generate_future_slots(region=region, now_utc=now)
    second_slot = future[1]

    await use_case(
        SelectSlotForPublicationRequest(
            publication_id=1,
            slot=second_slot,
            user_id=100,
            ad_id=1,
            now_utc=now,
            payment_confirmed=False,
        )
    )

    final = await pub_repo.get_by_id(1)
    assert final.status == PublicationStatus.SCHEDULED
