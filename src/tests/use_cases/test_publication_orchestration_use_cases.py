"""
Coverage for CreatePublicationFromAdUseCase and the three orchestration use
cases that compose it with SelectSlotForPublicationUseCase (CreateAndScheduleAdUseCase,
ReuseAdAndScheduleUseCase, FinalizeAndScheduleExistingAdUseCase) — previously
entirely untested. These are wired with real sub-use-case instances (not
mocks of each other) so the test actually exercises the composition, not
just that each piece gets called.
"""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from src.application.use_cases.ad.create_ad_draft import CreateAdDraftUseCase
from src.application.use_cases.ad.finalize_ad import FinalizeAdUseCase
from src.application.use_cases.ad.update_ad_content import UpdateAdContentUseCase
from src.application.use_cases.publication.create_ad_publication import (
    CreateAndScheduleAdRequest,
    CreateAndScheduleAdUseCase,
)
from src.application.use_cases.publication.create_publication_from_ad import (
    CreatePublicationFromAdRequest,
    CreatePublicationFromAdUseCase,
)
from src.application.use_cases.publication.finalize_and_schedule_existing_ad import (
    FinalizeAndScheduleExistingAdRequest,
    FinalizeAndScheduleExistingAdUseCase,
)
from src.application.use_cases.publication.reuse_ad_and_schedule import (
    ReuseAdAndScheduleRequest,
    ReuseAdAndScheduleUseCase,
)
from src.application.use_cases.publication.select_slot_for_publication import (
    SelectSlotForPublicationUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.region.region_guard import RegionGuard
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.redis.holt_store.in_memory import InMemorySlotHoldStore
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)
from src.infrastructure.scheduler.taskiq_queue_scheduler import TaskQueueScheduler
from src.utils.get_datetime_utc_now import get_datetime_utc_now


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}
        self._next_id = 100

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)

    async def create(self, ad: Ad) -> Ad:
        ad.id = self._next_id
        self._next_id += 1
        self._store[ad.id] = ad
        return ad

    async def save(self, ad: Ad) -> None:
        self._store[ad.id] = ad


class FakePublicationRepo:
    def __init__(self) -> None:
        self._store: dict[int, Publication] = {}
        self._next_id = 1000

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def create(self, publication: Publication) -> Publication:
        publication.id = self._next_id
        self._next_id += 1
        self._store[publication.id] = publication
        return publication

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication


class FakeRegionRepo:
    def __init__(self, region: Region) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        return self._region if self._region.id == region_id else None


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
        # system_paid_slots_count=0 so every slot in these tests is free,
        # keeping the scenario independent of wall-clock time.
        settings=RegionSettings(system_paid_slots_count=0),
    )


def build_select_slot_use_case(
    pub_repo: FakePublicationRepo,
    region_repo: FakeRegionRepo,
    task_queue: FakeTaskQueue,
) -> SelectSlotForPublicationUseCase:
    tx = FakeTransactionManager()
    scheduler = TaskQueueScheduler(
        queue=task_queue, publication_repo=pub_repo, transaction_manager=tx
    )
    reservation_service = SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        hold_ttl=timedelta(minutes=15),
    )
    settings = MagicMock()
    settings.app.debug = True
    settings.app.pre_publication_window_hours = 2

    return SelectSlotForPublicationUseCase(
        publication_repo=pub_repo,
        region_repo=region_repo,
        scheduler=scheduler,
        calendar_builder=CalendarBuilder(),
        time_resolver=PublishTimeResolver(),
        reservation_service=reservation_service,
        task_queue=task_queue,
        settings=settings,
        transaction_manager=tx,
    )


def fill_ready_content(ad: Ad) -> Ad:
    ad.fill_content(
        AdContent(
            plate_number="А001АА77",
            city="City",
            price=Price(100_000),
            contacts=Contacts(username="seller"),
        )
    )
    return ad


# ---------- CreatePublicationFromAdUseCase ----------


async def test_create_publication_from_ad_requires_ready_ad():
    ad = Ad(id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.DRAFT)
    use_case = CreatePublicationFromAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(CreatePublicationFromAdRequest(ad_id=1))


async def test_create_publication_from_ad_succeeds_for_ready_ad():
    ad = fill_ready_content(
        Ad(id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY)
    )
    use_case = CreatePublicationFromAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo(),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(CreatePublicationFromAdRequest(ad_id=1))

    assert dto.ad_id == 1
    assert dto.status == PublicationStatus.DRAFT


# ---------- ReuseAdAndScheduleUseCase ----------


async def test_reuse_ad_and_schedule_creates_and_schedules_publication():
    ad = fill_ready_content(
        Ad(id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY)
    )
    ad_repo = FakeAdRepo([ad])
    pub_repo = FakePublicationRepo()
    region = make_region()
    region_repo = FakeRegionRepo(region)
    task_queue = FakeTaskQueue()

    now = get_datetime_utc_now()
    future_slot = CalendarBuilder().generate_future_slots(region=region, now_utc=now)[0]

    use_case = ReuseAdAndScheduleUseCase(
        create_publication=CreatePublicationFromAdUseCase(
            ad_repo=ad_repo,
            publication_repo=pub_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        select_slot=build_select_slot_use_case(pub_repo, region_repo, task_queue),
    )

    dto = await use_case(
        ReuseAdAndScheduleRequest(ad_id=1, slot=future_slot, user_id=1)
    )

    final = await pub_repo.get_by_id(dto.id)
    assert final.status == PublicationStatus.SCHEDULED
    assert final.scheduler_job_id is not None


# ---------- FinalizeAndScheduleExistingAdUseCase ----------


async def test_finalize_and_schedule_existing_ad_full_pipeline():
    ad = fill_ready_content(
        Ad(id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY)
    )
    ad_repo = FakeAdRepo([ad])
    pub_repo = FakePublicationRepo()
    region = make_region()
    region_repo = FakeRegionRepo(region)
    task_queue = FakeTaskQueue()

    now = get_datetime_utc_now()
    future_slot = CalendarBuilder().generate_future_slots(region=region, now_utc=now)[0]

    use_case = FinalizeAndScheduleExistingAdUseCase(
        finalize_ad=FinalizeAdUseCase(ad_repo=ad_repo),
        create_publication=CreatePublicationFromAdUseCase(
            ad_repo=ad_repo,
            publication_repo=pub_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        select_slot=build_select_slot_use_case(pub_repo, region_repo, task_queue),
    )

    dto = await use_case(
        FinalizeAndScheduleExistingAdRequest(ad_id=1, slot=future_slot, user_id=1)
    )

    final = await pub_repo.get_by_id(dto.id)
    assert final.status == PublicationStatus.SCHEDULED


# ---------- CreateAndScheduleAdUseCase (full draft -> content -> finalize -> schedule) ----------


async def test_create_and_schedule_ad_full_pipeline():
    ad_repo = FakeAdRepo()
    pub_repo = FakePublicationRepo()
    region = make_region()
    region_repo = FakeRegionRepo(region)
    task_queue = FakeTaskQueue()

    now = get_datetime_utc_now()
    future_slot = CalendarBuilder().generate_future_slots(region=region, now_utc=now)[0]

    use_case = CreateAndScheduleAdUseCase(
        create_draft=CreateAdDraftUseCase(
            region_guard=RegionGuard(region_repo),
            ad_repo=ad_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        update_content=UpdateAdContentUseCase(
            ad_repo=ad_repo, transaction_manager=FakeTransactionManager()
        ),
        finalize_ad=FinalizeAdUseCase(ad_repo=ad_repo),
        create_publication=CreatePublicationFromAdUseCase(
            ad_repo=ad_repo,
            publication_repo=pub_repo,
            transaction_manager=FakeTransactionManager(),
        ),
        select_slot=build_select_slot_use_case(pub_repo, region_repo, task_queue),
    )

    dto = await use_case(
        CreateAndScheduleAdRequest(
            user_id=1,
            region_id=1,
            ad_type=AdType.SALE,
            plate="А001АА77",
            city="City",
            price=Price(100_000),
            contacts=Contacts(username="seller"),
            image_file_id="file-id",
            slot=future_slot,
            chat_id=555,
        )
    )

    final = await pub_repo.get_by_id(dto.id)
    assert final.status == PublicationStatus.SCHEDULED
    assert final.scheduler_job_id is not None
