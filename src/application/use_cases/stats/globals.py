from dataclasses import dataclass

from src.application.dtos.global_stats import (
    AdTypeCountDTO,
    GlobalStatsDTO,
    ServiceCountDTO,
)
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.region.region_repo import RegionRepository
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
    payment_repo: PaymentRepository

    async def __call__(self, command: GetGlobalStatsRequest) -> GlobalStatsDTO:
        since = command.period.since_utc()
        rid = command.region_id

        total_users = await self.user_repo.count_users(rid)
        with_store = await self.user_repo.count_users_with_store(rid)

        total_ads = await self.ad_repo.count_ads(since, rid)
        by_type_raw = await self.ad_repo.count_by_type(since, rid)
        scheduled = await self.publication_repo.count_scheduled(rid)

        total_services, by_service_raw = await self.publication_repo.count_services(
            since, rid
        )

        pay = await self.payment_repo.get_stats(since_utc=since, region_id=rid)

        total_regions = await self.region_repo.count_regions()

        return GlobalStatsDTO(
            total_users=total_users,
            users_with_store=with_store,
            users_without_store=total_users - with_store,
            total_ads=total_ads,
            scheduled_ads=scheduled,
            by_ad_type=[AdTypeCountDTO(ad_type=t, count=c) for t, c in by_type_raw],
            total_regions=total_regions,
            total_purchases=pay.total_count,
            total_amount=pay.total_amount,
            total_services=total_services,
            by_service=[ServiceCountDTO(type=t, count=c) for t, c in by_service_raw],
        )
