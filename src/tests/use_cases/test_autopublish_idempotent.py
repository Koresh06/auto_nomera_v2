"""
Regression test for AUD-21: AutopublishStrategy.apply() created child
publications in a loop and only called service.mark_used() at the very end.
If the process crashed mid-series (or apply() was invoked again for any
other reason while the service was still ACTIVE), a second call started the
loop over from day 1 and created duplicate child publications for days that
already existed.
"""

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from src.application.services.publication.context import ServiceContext
from src.application.services.publication.strategies.autopublish import (
    AutopublishStrategy,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName
from src.utils.get_datetime_utc_now import get_datetime_utc_now


class FakePublicationRepo:
    def __init__(self) -> None:
        self._store: dict[int, Publication] = {}
        self._next_id = 1000
        self.created: list[Publication] = []

    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        return [p for p in self._store.values() if p.ad_id == ad_id]

    async def create(self, publication: Publication) -> Publication:
        publication.id = self._next_id
        self._next_id += 1
        self._store[publication.id] = publication
        self.created.append(publication)
        return publication

    async def get_by_id(self, publication_id: int):
        return self._store.get(publication_id)

    async def save(self, publication: Publication) -> None:
        self._store[publication.id] = publication


class FakeScheduler:
    def __init__(self) -> None:
        self.scheduled: list[int] = []

    async def schedule_publication(self, *, publication_id: int, run_at_utc) -> None:
        self.scheduled.append(publication_id)


class FakeTaskQueue:
    async def schedule(self, *, task_name: str, args, run_at_utc) -> str | None:
        return "job-id"


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


def make_ad() -> Ad:
    return Ad(
        id=10, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.PUBLISHED
    )


async def test_second_apply_call_does_not_duplicate_already_created_days():
    region = make_region()
    tz = ZoneInfo(region.timezone.value)
    now_utc = get_datetime_utc_now()
    # родитель фактически опубликован 2 дня назад
    published_at_utc = (
        (now_utc - timedelta(days=2)).astimezone(tz).astimezone(timezone.utc)
    )

    publication_repo = FakePublicationRepo()
    scheduler = FakeScheduler()

    publication = Publication(
        id=1,
        ad_id=10,
        region_id=1,
        status=PublicationStatus.PUBLISHED,
        published_at_utc=published_at_utc,
    )

    service = PublicationService(
        id=1,
        type=PublicationServiceType.AUTOPUBLISH,
        status=PublicationServiceStatus.ACTIVE,
        params={"days": 5},
    )

    context = ServiceContext(
        region=region,
        ad=make_ad(),
        scheduler=scheduler,
        telegram=None,
        publication_repo=publication_repo,
        time_resolver=PublishTimeResolver(),
        image_processor=None,
        tg_id=1,
        caption="caption",
        task_queue=FakeTaskQueue(),
        pre_publication_window_hours=2,
    )

    strategy = AutopublishStrategy()

    await strategy.apply(publication, service, context)
    first_run_created = len(publication_repo.created)
    assert first_run_created > 0

    # Simulate the service having been left ACTIVE (as if mark_used() never
    # committed due to a crash) and apply() being invoked again.
    service.status = PublicationServiceStatus.ACTIVE
    await strategy.apply(publication, service, context)

    # No new publications should have been created the second time — every
    # day in the series already exists.
    assert len(publication_repo.created) == first_run_created
