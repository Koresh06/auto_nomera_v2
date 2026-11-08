from dataclasses import dataclass
from decimal import Decimal

from src.application.dtos.global_stats import (
    AdTypeCountDTO,
    GlobalStatsDTO,
    RegionActivityDTO,
    ServiceCountDTO,
)
from src.application.dtos.stats_report import ReportFilter, sum_metrics
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.stats.report_repo import StatsReportRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.period import StatsPeriod


@dataclass(frozen=True, eq=False)
class GetGlobalStatsRequest(UseCaseRequest):
    period: StatsPeriod
    region_id: int | None = None


@dataclass(kw_only=True)
class GetGlobalStatsUseCase(UseCase[GetGlobalStatsRequest, GlobalStatsDTO]):
    user_repo: UserRepository
    ad_repo: AdRepository
    publication_repo: PublicationRepository
    region_repo: RegionRepository
    report_repo: StatsReportRepository

    async def __call__(self, command: GetGlobalStatsRequest) -> GlobalStatsDTO:
        since = command.period.since_utc()
        rid = command.region_id

        total_users = await self.user_repo.count_users(since, rid)
        with_store = await self.user_repo.count_users_with_store(since, rid)

        total_ads = await self.ad_repo.count_ads(since, rid)
        by_type_raw = await self.ad_repo.count_by_type(since, rid)
        scheduled = await self.publication_repo.count_scheduled(rid)

        total_services, by_service_raw = await self.publication_repo.count_services(
            since, rid
        )

        # те же показатели, что в выгрузке, иначе бот и Excel разойдутся:
        # платежи содержат пополнения, но не покупки с баланса
        metrics = await self.report_repo.get_region_metrics(
            ReportFilter(since_utc=since, region_ids=(rid,) if rid else ())
        )
        totals = sum_metrics(metrics.values())

        total_regions = await self.region_repo.count_regions()

        top_regions: list[RegionActivityDTO] = []
        if rid is None:
            top_raw = await self.ad_repo.top_regions_by_activity(since, limit=5)
            top_regions = [
                RegionActivityDTO(title=title, count=count) for title, count in top_raw
            ]

        return GlobalStatsDTO(
            total_users=total_users,
            users_with_store=with_store,
            users_without_store=total_users - with_store,
            total_ads=total_ads,
            scheduled_ads=scheduled,
            by_ad_type=[AdTypeCountDTO(ad_type=t, count=c) for t, c in by_type_raw],
            total_regions=total_regions,
            total_purchases=int(totals.get("revenue_count", Decimal("0"))),
            total_amount=totals.get("revenue_total", Decimal("0")),
            total_services=total_services,
            by_service=[ServiceCountDTO(type=t, count=c) for t, c in by_service_raw],
            top_regions=top_regions,
        )
