"""
Coverage for src/application/use_cases/ad/* (except ensure_ad_image_ref,
which depends on a real aiogram Bot and isn't worth mocking at this layer) —
previously entirely untested.
"""

import pytest

from src.application.exceptions.ad import (
    AdAlreadyProcessedException,
    AdNotFoundException,
)
from src.application.use_cases.ad.approve_urgent_buyout import (
    ApproveUrgentBuyoutRequest,
    ApproveUrgentBuyoutUseCase,
)
from src.application.use_cases.ad.archive_ad import ArchiveAdRequest, ArchiveAdUseCase
from src.application.use_cases.ad.cancel_ad_draft_reminder import (
    CancelAdDraftReminderRequest,
    CancelAdDraftReminderUseCase,
)
from src.application.use_cases.ad.count_ads_by_user import (
    CountAdsByUserRequest,
    CountAdsByUserUseCase,
)
from src.application.use_cases.ad.create_ad_draft import (
    CreateAdDraftRequest,
    CreateAdDraftUseCase,
)
from src.application.use_cases.ad.eject_urgent_buyout import (
    RejectUrgentBuyoutRequest,
    RejectUrgentBuyoutUseCase,
)
from src.application.use_cases.ad.finalize_ad import (
    FinalizeAdRequest,
    FinalizeAdUseCase,
)
from src.application.use_cases.ad.find_by_plate import (
    FindAdByPlateRequest,
    FindAdByPlateUseCase,
)
from src.application.use_cases.ad.get_by_id import GetByIdAdRequest, GetByIdAdUseCase
from src.application.use_cases.ad.schedule_ad_draft_reminder import (
    ScheduleAdDraftReminderRequest,
    ScheduleAdDraftReminderUseCase,
)
from src.application.use_cases.ad.update_ad_content import (
    UpdateAdContentRequest,
    UpdateAdContentUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.region import RegionStatus
from src.domain.exceptions.region import RegionDisabledError
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}
        self._next_id = 100
        self.created: list[Ad] = []
        self.saved: list[Ad] = []

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)

    async def create(self, ad: Ad) -> Ad:
        ad.id = self._next_id
        self._next_id += 1
        self._store[ad.id] = ad
        self.created.append(ad)
        return ad

    async def save(self, ad: Ad) -> None:
        self.saved.append(ad)
        self._store[ad.id] = ad

    async def find_by_plate(self, user_id: int, region_id: int, plate_number: str):
        for ad in self._store.values():
            if (
                ad.content
                and ad.content.plate_number == plate_number
                and ad.user_id == user_id
                and ad.region_id == region_id
            ):
                return ad
        return None

    async def count_ads_by_user(self, user_id: int, region_id: int) -> int:
        return sum(
            1
            for a in self._store.values()
            if a.user_id == user_id and a.region_id == region_id
        )


class FakePublicationRepo:
    def __init__(self, pubs: list[Publication] | None = None) -> None:
        self._store = {p.id: p for p in (pubs or [])}
        self.saved: list[Publication] = []

    async def get_by_id(self, publication_id: int):
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self.saved.append(publication)
        self._store[publication.id] = publication

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        return [p for p in self._store.values() if p.ad_id == ad_id]


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple]] = []
        self.cancelled: list[str] = []
        self.scheduled: list[tuple] = []

    async def enqueue(self, *, task_name: str, args: tuple) -> str | None:
        self.enqueued.append((task_name, args))
        return "job-id"

    async def cancel(self, *, job_id: str) -> bool:
        self.cancelled.append(job_id)
        return True

    async def schedule(self, *, task_name: str, args: tuple, run_at_utc) -> str | None:
        self.scheduled.append((task_name, args, run_at_utc))
        return "job-id"


class FakeDraftReminderStore:
    def __init__(self) -> None:
        self._jobs: dict[int, str] = {}
        self.set_calls: list[tuple[int, str, int]] = []
        self.deleted: list[int] = []

    async def get_job_id(self, user_id: int) -> str | None:
        return self._jobs.get(user_id)

    async def set_job_id(self, user_id: int, job_id: str, ttl_seconds: int) -> None:
        self._jobs[user_id] = job_id
        self.set_calls.append((user_id, job_id, ttl_seconds))

    async def delete(self, user_id: int) -> None:
        self._jobs.pop(user_id, None)
        self.deleted.append(user_id)


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


def make_region(status: RegionStatus = RegionStatus.ACTIVE) -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=status,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


def make_ad(**overrides) -> Ad:
    defaults = dict(
        id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.READY
    )
    defaults.update(overrides)
    return Ad(**defaults)


# ---------- ApproveUrgentBuyoutUseCase ----------


async def test_approve_urgent_buyout_publishes_and_notifies():
    ad = make_ad(ad_type=AdType.URGENT_BUYOUT, status=AdStatus.PENDING_MODERATION)
    queue = FakeTaskQueue()
    use_case = ApproveUrgentBuyoutUseCase(
        ad_repo=FakeAdRepo([ad]),
        task_queue=queue,
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(ApproveUrgentBuyoutRequest(ad_id=1))

    assert ad.status == AdStatus.PUBLISHED
    assert queue.enqueued == [("notify_pre_publication_users", (1,))]


async def test_approve_urgent_buyout_rejects_already_processed():
    ad = make_ad(ad_type=AdType.URGENT_BUYOUT, status=AdStatus.PUBLISHED)
    use_case = ApproveUrgentBuyoutUseCase(
        ad_repo=FakeAdRepo([ad]),
        task_queue=FakeTaskQueue(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(AdAlreadyProcessedException):
        await use_case(ApproveUrgentBuyoutRequest(ad_id=1))


async def test_approve_urgent_buyout_unknown_ad_raises():
    use_case = ApproveUrgentBuyoutUseCase(
        ad_repo=FakeAdRepo([]),
        task_queue=FakeTaskQueue(),
        transaction_manager=FakeTransactionManager(),
    )
    with pytest.raises(AdNotFoundException):
        await use_case(ApproveUrgentBuyoutRequest(ad_id=1))


# ---------- RejectUrgentBuyoutUseCase ----------


async def test_reject_urgent_buyout_archives_ad():
    ad = make_ad(ad_type=AdType.URGENT_BUYOUT, status=AdStatus.PENDING_MODERATION)
    use_case = RejectUrgentBuyoutUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    await use_case(RejectUrgentBuyoutRequest(ad_id=1))

    assert ad.status == AdStatus.ARCHIVED


async def test_reject_urgent_buyout_rejects_already_processed():
    ad = make_ad(ad_type=AdType.URGENT_BUYOUT, status=AdStatus.ARCHIVED)
    use_case = RejectUrgentBuyoutUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(AdAlreadyProcessedException):
        await use_case(RejectUrgentBuyoutRequest(ad_id=1))


# ---------- ArchiveAdUseCase ----------


async def test_archive_ad_marks_ad_archived():
    ad = make_ad()
    use_case = ArchiveAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([]),
        task_queue=FakeTaskQueue(),
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(ArchiveAdRequest(ad_id=1))

    assert ad.status == AdStatus.ARCHIVED


async def test_archive_ad_cancels_publication_and_scheduler_job():
    ad = make_ad()
    pub = Publication(
        id=5,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        scheduler_job_id="job-5",
    )
    queue = FakeTaskQueue()
    use_case = ArchiveAdUseCase(
        ad_repo=FakeAdRepo([ad]),
        publication_repo=FakePublicationRepo([pub]),
        task_queue=queue,
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(ArchiveAdRequest(ad_id=1, publication_id=5))

    assert pub.status == PublicationStatus.CANCELED
    assert queue.cancelled == ["job-5"]


async def test_archive_ad_unknown_ad_raises():
    use_case = ArchiveAdUseCase(
        ad_repo=FakeAdRepo([]),
        publication_repo=FakePublicationRepo([]),
        task_queue=FakeTaskQueue(),
        transaction_manager=FakeTransactionManager(),
    )
    with pytest.raises(AdNotFoundException):
        await use_case(ArchiveAdRequest(ad_id=1))


# ---------- CancelAdDraftReminderUseCase ----------


async def test_cancel_ad_draft_reminder_noop_when_no_job():
    queue = FakeTaskQueue()
    use_case = CancelAdDraftReminderUseCase(
        task_queue=queue, reminder_store=FakeDraftReminderStore()
    )

    await use_case(CancelAdDraftReminderRequest(user_id=1))

    assert queue.cancelled == []


async def test_cancel_ad_draft_reminder_cancels_existing_job():
    store = FakeDraftReminderStore()
    await store.set_job_id(1, "job-1", 3600)
    queue = FakeTaskQueue()
    use_case = CancelAdDraftReminderUseCase(task_queue=queue, reminder_store=store)

    await use_case(CancelAdDraftReminderRequest(user_id=1))

    assert queue.cancelled == ["job-1"]
    assert store.deleted == [1]


# ---------- CountAdsByUserUseCase ----------


async def test_count_ads_by_user_delegates_to_repo():
    ads = [make_ad(id=1, user_id=5, region_id=2), make_ad(id=2, user_id=5, region_id=2)]
    use_case = CountAdsByUserUseCase(ad_repo=FakeAdRepo(ads))

    result = await use_case(CountAdsByUserRequest(user_id=5, region_id=2))

    assert result == 2


# ---------- CreateAdDraftUseCase ----------


async def test_create_ad_draft_succeeds_for_active_region():
    region = make_region()
    repo = FakeAdRepo()
    use_case = CreateAdDraftUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=repo,
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        CreateAdDraftRequest(
            user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.DRAFT
        )
    )

    assert dto.ad_type == AdType.SALE
    assert len(repo.created) == 1


async def test_create_ad_draft_rejects_disabled_region():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = CreateAdDraftUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        ad_repo=FakeAdRepo(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(RegionDisabledError):
        await use_case(
            CreateAdDraftRequest(
                user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.DRAFT
            )
        )


# ---------- FinalizeAdUseCase ----------


async def test_finalize_ad_standard_requires_content():
    ad = make_ad(ad_type=AdType.SALE)
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([ad]))

    with pytest.raises(ValueError):
        await use_case(FinalizeAdRequest(ad_id=1))


async def test_finalize_ad_standard_succeeds_with_valid_content():
    from src.domain.value_objects.ad_content import AdContent

    ad = make_ad(ad_type=AdType.SALE)
    ad.fill_content(
        AdContent(
            plate_number="А001АА77",
            city="City",
            price=Price(100_000),
            contacts=Contacts(username="seller"),
        )
    )
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([ad]))

    await use_case(FinalizeAdRequest(ad_id=1))  # must not raise


async def test_finalize_ad_rejects_masked_plate_for_sale():
    from src.domain.value_objects.ad_content import AdContent

    ad = make_ad(ad_type=AdType.SALE)
    ad.fill_content(
        AdContent(
            plate_number="А***АА77",
            city="City",
            price=Price(100_000),
            contacts=Contacts(username="seller"),
        )
    )
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([ad]))

    with pytest.raises(ValueError):
        await use_case(FinalizeAdRequest(ad_id=1))


async def test_finalize_ad_allows_masked_plate_for_buy():
    from src.domain.value_objects.ad_content import AdContent

    ad = make_ad(ad_type=AdType.BUY)
    ad.fill_content(
        AdContent(
            plate_number="А***АА77",
            city="City",
            price=Price(0),
            contacts=Contacts(username="buyer"),
        )
    )
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([ad]))

    await use_case(FinalizeAdRequest(ad_id=1))  # must not raise


async def test_finalize_ad_store_requires_items():
    from src.domain.value_objects.store_content import StoreContent

    ad = make_ad(ad_type=AdType.STORE)
    ad.fill_store_content(
        StoreContent(
            shop_name="Shop", city="City", contacts=Contacts(username="s"), items=()
        )
    )
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([ad]))

    with pytest.raises(ValueError):
        await use_case(FinalizeAdRequest(ad_id=1))


async def test_finalize_ad_unknown_ad_raises():
    use_case = FinalizeAdUseCase(ad_repo=FakeAdRepo([]))
    with pytest.raises(AdNotFoundException):
        await use_case(FinalizeAdRequest(ad_id=1))


# ---------- FindAdByPlateUseCase / GetByIdAdUseCase ----------


async def test_find_ad_by_plate_returns_none_when_missing():
    use_case = FindAdByPlateUseCase(ad_repo=FakeAdRepo([]))
    result = await use_case(
        FindAdByPlateRequest(user_id=1, region_id=1, plate_number="А001АА77")
    )
    assert result is None


async def test_get_by_id_ad_raises_when_missing():
    use_case = GetByIdAdUseCase(ad_repo=FakeAdRepo([]))
    with pytest.raises(AdNotFoundException):
        await use_case(GetByIdAdRequest(ad_id=1))


async def test_get_by_id_ad_returns_dto():
    use_case = GetByIdAdUseCase(ad_repo=FakeAdRepo([make_ad()]))
    dto = await use_case(GetByIdAdRequest(ad_id=1))
    assert dto.id == 1


# ---------- ScheduleAdDraftReminderUseCase ----------


async def test_schedule_ad_draft_reminder_schedules_new_job():
    queue = FakeTaskQueue()
    store = FakeDraftReminderStore()
    use_case = ScheduleAdDraftReminderUseCase(task_queue=queue, reminder_store=store)

    await use_case(ScheduleAdDraftReminderRequest(user_id=1, tg_id=1001))

    assert len(queue.scheduled) == 1
    assert queue.scheduled[0][0] == "send_ad_draft_reminder"
    assert store.set_calls[0][0] == 1


async def test_schedule_ad_draft_reminder_cancels_previous_job_first():
    queue = FakeTaskQueue()
    store = FakeDraftReminderStore()
    await store.set_job_id(1, "old-job", 3600)
    use_case = ScheduleAdDraftReminderUseCase(task_queue=queue, reminder_store=store)

    await use_case(ScheduleAdDraftReminderRequest(user_id=1, tg_id=1001))

    assert queue.cancelled == ["old-job"]


# ---------- UpdateAdContentUseCase ----------


async def test_update_ad_content_standard_merges_with_existing():
    from src.domain.value_objects.ad_content import AdContent

    ad = make_ad(ad_type=AdType.SALE)
    ad.fill_content(
        AdContent(
            plate_number="А001АА77",
            city="OldCity",
            price=Price(100),
            contacts=Contacts(username="seller"),
        )
    )
    use_case = UpdateAdContentUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    await use_case(UpdateAdContentRequest(ad_id=1, city="NewCity"))

    assert ad.content.city == "NewCity"
    assert ad.content.plate_number == "А001АА77"  # unchanged


async def test_update_ad_content_store_validates_items():
    from src.domain.value_objects.store_content import StoreContent

    ad = make_ad(ad_type=AdType.STORE)
    ad.fill_store_content(
        StoreContent(shop_name="Shop", city="City", contacts=Contacts(), items=())
    )
    use_case = UpdateAdContentUseCase(
        ad_repo=FakeAdRepo([ad]), transaction_manager=FakeTransactionManager()
    )

    await use_case(
        UpdateAdContentRequest(ad_id=1, store_items=[("А001АА77", Price(100_000))])
    )

    assert ad.store_content.items[0].plate == "А001АА77"


async def test_update_ad_content_unknown_ad_raises():
    use_case = UpdateAdContentUseCase(
        ad_repo=FakeAdRepo([]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(AdNotFoundException):
        await use_case(UpdateAdContentRequest(ad_id=1, city="X"))
