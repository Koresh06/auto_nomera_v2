"""
Coverage for the read-side publication use cases: check_limiter,
get_admin_scheduled_catalog, get_all_user_publications, get_by_id,
get_overdue_unpublished, get_user — previously entirely untested.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.application.exceptions.publication import PublicationNotFoundException
from src.application.use_cases.publication.check_limiter import (
    CheckPublicationLimitRequest,
    CheckPublicationLimitUseCase,
)
from src.application.use_cases.publication.get_admin_scheduled_catalog import (
    GetAdminScheduledCatalogRequest,
    GetAdminScheduledCatalogUseCase,
)
from src.application.use_cases.publication.get_all_user_publications import (
    GetAllUserPublicationsRequest,
    GetAllUserPublicationsUseCase,
)
from src.application.use_cases.publication.get_by_id import (
    GetPublicationByIdRequest,
    GetPublicationByIdUseCase,
)
from src.application.use_cases.publication.get_overdue_unpublished import (
    GetOverdueUnpublishedRequest,
    GetOverdueUnpublishedUseCase,
)
from src.application.use_cases.publication.get_user import (
    GetUserPublicationsRequest,
    GetUserPublicationsUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.region import RegionStatus
from src.domain.exceptions.region import RegionDisabledError
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.timezone_name import TimezoneName


class FakePublicationRepo:
    def __init__(self, pubs: list[Publication] | None = None) -> None:
        self._store = {p.id: p for p in (pubs or [])}
        self.count_result = 0
        self.find_last_result: Publication | None = None
        self.list_all_by_user_rows: list[tuple] = []
        self.list_by_user_rows: list[tuple] = []
        self.list_for_catalog_rows: list[tuple] = []
        self.overdue_rows: list[tuple] = []

    async def get_by_id(self, publication_id: int) -> Publication | None:
        return self._store.get(publication_id)

    async def count_scheduled_by_user(self, **kwargs) -> int:
        return self.count_result

    async def find_last_by_plate(self, **kwargs):
        return self.find_last_result

    async def list_all_by_user(self, user_id: int, region_id: int):
        return self.list_all_by_user_rows

    async def list_by_user(self, user_id: int, region_id: int):
        return self.list_by_user_rows

    async def list_scheduled_for_catalog(self, region_id: int):
        return self.list_for_catalog_rows

    async def list_overdue_scheduled_today(self, now_utc):
        return self.overdue_rows


class FakeAdRepo:
    def __init__(self, ads: list[Ad] | None = None) -> None:
        self._store = {a.id: a for a in (ads or [])}

    async def get_by_id(self, ad_id: int) -> Ad | None:
        return self._store.get(ad_id)


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


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


# ---------- CheckPublicationLimitUseCase ----------


async def test_check_limiter_allows_when_disabled_in_settings():
    region = make_region(settings=RegionSettings(publication_limit_enabled=False))
    use_case = CheckPublicationLimitUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        publication_repo=FakePublicationRepo(),
        ad_repo=FakeAdRepo(),
        region_repo=FakeRegionRepo(region),
    )

    result = await use_case(
        CheckPublicationLimitRequest(
            user_id=1,
            region_id=1,
            ad_type=AdType.SALE,
            plate="А001АА77",
            publish_at_utc=datetime.now(timezone.utc),
            region_timezone="Europe/Moscow",
        )
    )

    assert result.allowed is True


async def test_check_limiter_denies_when_count_at_limit():
    region = make_region()
    pub_repo = FakePublicationRepo()
    pub_repo.count_result = 5  # FREE_LIMITS[SALE] == 5
    use_case = CheckPublicationLimitUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        publication_repo=pub_repo,
        ad_repo=FakeAdRepo(),
        region_repo=FakeRegionRepo(region),
    )

    result = await use_case(
        CheckPublicationLimitRequest(
            user_id=1,
            region_id=1,
            ad_type=AdType.SALE,
            plate="А001АА77",
            publish_at_utc=datetime.now(timezone.utc),
            region_timezone="Europe/Moscow",
        )
    )

    assert result.allowed is False
    assert "лимит" in result.reason.lower()


async def test_check_limiter_denies_when_plate_published_too_recently():
    region = make_region()
    pub_repo = FakePublicationRepo()
    pub_repo.count_result = 0
    now = datetime.now(timezone.utc)
    pub_repo.find_last_result = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.PUBLISHED,
        publish_at_utc=now - timedelta(days=1),
    )
    use_case = CheckPublicationLimitUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        publication_repo=pub_repo,
        ad_repo=FakeAdRepo(),
        region_repo=FakeRegionRepo(region),
    )

    result = await use_case(
        CheckPublicationLimitRequest(
            user_id=1,
            region_id=1,
            ad_type=AdType.SALE,
            plate="А001АА77",
            publish_at_utc=now,
            region_timezone="Europe/Moscow",
        )
    )

    assert result.allowed is False


async def test_check_limiter_store_ad_skips_plate_interval_check():
    """Store ads have no single plate, so the plate-interval check (which
    would need command.plate) must be skipped entirely."""
    region = make_region()
    pub_repo = FakePublicationRepo()
    pub_repo.count_result = 0
    use_case = CheckPublicationLimitUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        publication_repo=pub_repo,
        ad_repo=FakeAdRepo(),
        region_repo=FakeRegionRepo(region),
    )

    result = await use_case(
        CheckPublicationLimitRequest(
            user_id=1,
            region_id=1,
            ad_type=AdType.STORE,
            plate=None,
            publish_at_utc=datetime.now(timezone.utc),
            region_timezone="Europe/Moscow",
        )
    )

    assert result.allowed is True


async def test_check_limiter_raises_for_disabled_region():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = CheckPublicationLimitUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        publication_repo=FakePublicationRepo(),
        ad_repo=FakeAdRepo(),
        region_repo=FakeRegionRepo(region),
    )

    with pytest.raises(RegionDisabledError):
        await use_case(
            CheckPublicationLimitRequest(
                user_id=1,
                region_id=1,
                ad_type=AdType.SALE,
                plate="А001АА77",
                publish_at_utc=datetime.now(timezone.utc),
                region_timezone="Europe/Moscow",
            )
        )


# ---------- GetPublicationByIdUseCase ----------


async def test_get_publication_by_id_raises_when_missing():
    use_case = GetPublicationByIdUseCase(publication_repo=FakePublicationRepo())
    with pytest.raises(PublicationNotFoundException):
        await use_case(GetPublicationByIdRequest(publication_id=1))


async def test_get_publication_by_id_returns_dto():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    use_case = GetPublicationByIdUseCase(publication_repo=FakePublicationRepo([pub]))
    dto = await use_case(GetPublicationByIdRequest(publication_id=1))
    assert dto.id == 1


# ---------- GetAllUserPublicationsUseCase / GetUserPublicationsUseCase ----------


async def test_get_all_user_publications_maps_rows_to_dto():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    repo = FakePublicationRepo()
    repo.list_all_by_user_rows = [(pub, "А001АА77", None)]
    use_case = GetAllUserPublicationsUseCase(publication_repo=repo)

    result = await use_case(GetAllUserPublicationsRequest(user_id=1, region_id=1))

    assert len(result) == 1
    assert result[0].plate_number == "А001АА77"


async def test_get_user_publications_maps_rows_to_dto():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    repo = FakePublicationRepo()
    repo.list_by_user_rows = [(pub, None, "My Shop")]
    use_case = GetUserPublicationsUseCase(publication_repo=repo)

    result = await use_case(GetUserPublicationsRequest(user_id=1, region_id=1))

    assert len(result) == 1
    assert result[0].shop_name == "My Shop"


# ---------- GetAdminScheduledCatalogUseCase ----------


async def test_get_admin_scheduled_catalog_maps_rows():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    ad = Ad(
        id=1, user_id=1, region_id=1, ad_type=AdType.SALE, status=AdStatus.SCHEDULED
    )
    repo = FakePublicationRepo()
    repo.list_for_catalog_rows = [(pub, ad, 12345)]
    use_case = GetAdminScheduledCatalogUseCase(
        publication_repo=repo, ad_repo=FakeAdRepo([ad])
    )

    result = await use_case(GetAdminScheduledCatalogRequest(region_id=1))

    assert len(result) == 1
    assert result[0].ad.id == 1
    assert result[0].publication.id == 1
    assert result[0].is_urgent is False


# ---------- GetOverdueUnpublishedUseCase ----------


async def test_get_overdue_unpublished_uses_shop_name_for_store():
    slot = SlotKey(
        region_id=1,
        local_day=datetime.now(timezone.utc).date(),
        local_time=datetime.now(timezone.utc).time(),
    )
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    pub.slot = slot
    repo = FakePublicationRepo()
    repo.overdue_rows = [
        (pub, None, AdType.STORE, "user1", 111, "My Shop", "Europe/Moscow")
    ]
    use_case = GetOverdueUnpublishedUseCase(publication_repo=repo)

    result = await use_case(GetOverdueUnpublishedRequest())

    assert len(result) == 1
    assert result[0].plate_number == "My Shop"
    assert result[0].owner_link == '<a href="https://t.me/user1">👤</a>'


async def test_get_overdue_unpublished_uses_plate_for_non_store():
    pub = Publication(id=1, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED)
    repo = FakePublicationRepo()
    repo.overdue_rows = [
        (pub, "А001АА77", AdType.SALE, None, 222, None, "Europe/Moscow")
    ]
    use_case = GetOverdueUnpublishedUseCase(publication_repo=repo)

    result = await use_case(GetOverdueUnpublishedRequest())

    assert result[0].plate_number == "А001АА77"
    assert result[0].owner_link == '<a href="tg://user?id=222">👤</a>'
    assert result[0].local_time_label == "—"  # no slot set
