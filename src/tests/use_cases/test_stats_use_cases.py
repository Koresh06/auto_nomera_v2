"""
Coverage for src/application/use_cases/stats/* — previously entirely
untested.
"""

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from src.application.dtos.payment_stats import PaymentStatsDTO, RegionStatDTO
from src.application.dtos.publication_stats import PublicationStatsDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.use_cases.stats.globals import (
    GetGlobalStatsRequest,
    GetGlobalStatsUseCase,
)
from src.application.use_cases.stats.payment import (
    GetPaymentStatsRequest,
    GetPaymentStatsUseCase,
    GetRegionBreakdownRequest,
    GetRegionBreakdownUseCase,
)
from src.application.use_cases.stats.publication import (
    GetPublicationStatsRequest,
    GetPublicationStatsUseCase,
)
from src.application.use_cases.stats.region_schedule import (
    GetRegionScheduleRequest,
    GetRegionScheduleUseCase,
)
from src.domain.entities.publication import Publication
from src.domain.entities.region import Region
from src.domain.enums.ad import AdType
from src.domain.enums.period import StatsPeriod
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeUserRepo:
    async def count_users(self, since_utc, region_id) -> int:
        return 100

    async def count_users_with_store(self, since_utc, region_id) -> int:
        return 20


class FakeAdRepo:
    async def count_ads(self, since_utc, region_id) -> int:
        return 50

    async def count_by_type(self, since_utc, region_id):
        return [(AdType.SALE, 30), (AdType.BUY, 20)]

    async def top_regions_by_activity(self, since_utc, limit=5):
        return [("Москва", 10)]


class FakePublicationRepo:
    def __init__(self) -> None:
        self.schedule_rows: list[tuple] = []

    async def count_scheduled(self, region_id) -> int:
        return 15

    async def count_services(self, since_utc, region_id):
        return 5, [("pin", 3), ("highlight", 2)]

    async def get_stats(self, *, since_utc, region_id) -> PublicationStatsDTO:
        return PublicationStatsDTO(
            total=10,
            by_status=[],
            by_ad_type=[],
            top_region_title=None,
            top_region_count=0,
        )

    async def list_scheduled_by_region(self, region_id, from_utc, to_utc):
        return self.schedule_rows


class FakeRegionRepo:
    def __init__(self, region: Region | None = None) -> None:
        self._region = region

    async def count_regions(self) -> int:
        return 7

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakePaymentRepo:
    def __init__(self) -> None:
        self.stats_result = PaymentStatsDTO(
            total_count=3,
            total_amount=Decimal("500"),
            by_method=[],
            top_region=None,
            stars_total=0,
        )
        self.breakdown_result = [
            RegionStatDTO(
                region_id=1, region_title="Москва", count=3, amount=Decimal("500")
            )
        ]

    async def get_stats(self, *, since_utc, region_id) -> PaymentStatsDTO:
        return self.stats_result

    async def get_region_breakdown(self, *, since_utc):
        return self.breakdown_result


def make_region(**overrides) -> Region:
    defaults = dict(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        metadata=RegionMetadata(),
        settings=RegionSettings(days_range=3),
    )
    defaults.update(overrides)
    return Region(**defaults)


# ---------- GetGlobalStatsUseCase ----------


async def test_get_global_stats_aggregates_everything():
    use_case = GetGlobalStatsUseCase(
        user_repo=FakeUserRepo(),
        ad_repo=FakeAdRepo(),
        publication_repo=FakePublicationRepo(),
        region_repo=FakeRegionRepo(),
        payment_repo=FakePaymentRepo(),
    )

    result = await use_case(GetGlobalStatsRequest(period=StatsPeriod.WEEK))

    assert result.total_users == 100
    assert result.users_with_store == 20
    assert result.users_without_store == 80
    assert result.total_ads == 50
    assert result.scheduled_ads == 15
    assert result.total_regions == 7
    assert result.total_purchases == 3
    assert result.total_amount == Decimal("500")
    assert result.total_services == 5
    assert len(result.top_regions) == 1  # region_id is None -> top_regions populated


async def test_get_global_stats_skips_top_regions_when_region_id_given():
    use_case = GetGlobalStatsUseCase(
        user_repo=FakeUserRepo(),
        ad_repo=FakeAdRepo(),
        publication_repo=FakePublicationRepo(),
        region_repo=FakeRegionRepo(),
        payment_repo=FakePaymentRepo(),
    )

    result = await use_case(GetGlobalStatsRequest(period=StatsPeriod.WEEK, region_id=1))

    assert result.top_regions == []


# ---------- GetPaymentStatsUseCase / GetRegionBreakdownUseCase ----------


async def test_get_payment_stats_delegates_to_repo():
    repo = FakePaymentRepo()
    use_case = GetPaymentStatsUseCase(payment_repo=repo)

    result = await use_case(GetPaymentStatsRequest(period=StatsPeriod.MONTH))

    assert result is repo.stats_result


async def test_get_region_breakdown_delegates_to_repo():
    repo = FakePaymentRepo()
    use_case = GetRegionBreakdownUseCase(payment_repo=repo)

    result = await use_case(GetRegionBreakdownRequest(period=StatsPeriod.ALL))

    assert result == repo.breakdown_result


# ---------- GetPublicationStatsUseCase ----------


async def test_get_publication_stats_delegates_to_repo():
    use_case = GetPublicationStatsUseCase(publication_repo=FakePublicationRepo())

    result = await use_case(GetPublicationStatsRequest(period=StatsPeriod.TODAY))

    assert result.total == 10


# ---------- GetRegionScheduleUseCase ----------


async def test_get_region_schedule_raises_when_region_missing():
    use_case = GetRegionScheduleUseCase(
        publication_repo=FakePublicationRepo(), region_repo=FakeRegionRepo()
    )
    with pytest.raises(RegionNotFoundException):
        await use_case(GetRegionScheduleRequest(region_id=1))


async def test_get_region_schedule_groups_by_date_and_uses_shop_name_for_store():
    region = make_region(settings=RegionSettings(days_range=2))
    pub_repo = FakePublicationRepo()
    now_local = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Moscow"))
    pub1 = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        publish_at_utc=now_local.astimezone(timezone.utc),
    )
    pub_repo.schedule_rows = [
        (pub1, None, AdType.STORE, "owner1", 111, "My Shop", True, False),
    ]

    use_case = GetRegionScheduleUseCase(
        publication_repo=pub_repo, region_repo=FakeRegionRepo(region)
    )

    result = await use_case(GetRegionScheduleRequest(region_id=1))

    assert result.region_title == "Test"
    assert len(result.days) == 2  # days_range == 2
    today_slots = result.days[0].slots
    assert len(today_slots) == 1
    assert today_slots[0].plate == "My Shop"
    assert today_slots[0].is_paid is True


async def test_get_region_schedule_skips_publications_without_publish_at():
    region = make_region(settings=RegionSettings(days_range=1))
    pub_repo = FakePublicationRepo()
    pub_no_time = Publication(
        id=1, ad_id=1, region_id=1, status=PublicationStatus.DRAFT, publish_at_utc=None
    )
    pub_repo.schedule_rows = [
        (pub_no_time, "А001АА77", AdType.SALE, None, 222, None, False, False),
    ]

    use_case = GetRegionScheduleUseCase(
        publication_repo=pub_repo, region_repo=FakeRegionRepo(region)
    )

    result = await use_case(GetRegionScheduleRequest(region_id=1))

    assert result.days[0].count == 0


async def test_region_schedule_days_follow_region_local_date(monkeypatch):
    """«Сегодня» в расписании — по местной дате региона, а не по UTC.
    09.10 22:00 UTC = 10.10 08:00 во Владивостоке: первый день расписания
    10.10, утренняя публикация 10.10 — в нём, а не в «следующем» дне."""
    from src.application.use_cases.stats import region_schedule as module

    fixed_now = datetime(2026, 10, 9, 22, 0, tzinfo=timezone.utc)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now.astimezone(tz) if tz else fixed_now

    monkeypatch.setattr(module, "datetime", FrozenDatetime)

    region = make_region(
        timezone=TimezoneName("Asia/Vladivostok"),
        settings=RegionSettings(days_range=2),
    )
    pub_repo = FakePublicationRepo()
    morning = Publication(
        id=1,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.SCHEDULED,
        # 10.10 10:00 по Владивостоку
        publish_at_utc=datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    pub_repo.schedule_rows = [
        (morning, "А001АА77", AdType.SALE, None, 1, None, False, False)
    ]
    use_case = GetRegionScheduleUseCase(
        publication_repo=pub_repo, region_repo=FakeRegionRepo(region)
    )

    result = await use_case(GetRegionScheduleRequest(region_id=1))

    assert [d.date for d in result.days] == ["10.10.2026", "11.10.2026"]
    assert [s.time for s in result.days[0].slots] == ["10:00"]
