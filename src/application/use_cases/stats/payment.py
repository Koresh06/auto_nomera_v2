from dataclasses import dataclass

from src.application.dtos.stats import PaymentStatsDTO, RegionStatDTO
from src.application.ports.payment.payment_repo import PaymentRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.period import StatsPeriod


@dataclass(frozen=True, eq=False)
class GetPaymentStatsRequest(UseCaseRequest):
    period: StatsPeriod
    region_id: int | None = None


@dataclass(kw_only=True)
class GetPaymentStatsUseCase(UseCase[GetPaymentStatsRequest, PaymentStatsDTO]):
    payment_repo: PaymentRepository

    async def __call__(self, command: GetPaymentStatsRequest) -> PaymentStatsDTO:
        return await self.payment_repo.get_stats(
            since_utc=command.period.since_utc(),
            region_id=command.region_id,
        )


@dataclass(frozen=True, eq=False)
class GetRegionBreakdownRequest(UseCaseRequest):
    period: StatsPeriod


@dataclass(kw_only=True)
class GetRegionBreakdownUseCase(
    UseCase[GetRegionBreakdownRequest, list[RegionStatDTO]]
):
    payment_repo: PaymentRepository

    async def __call__(self, command: GetRegionBreakdownRequest) -> list[RegionStatDTO]:
        return await self.payment_repo.get_region_breakdown(
            since_utc=command.period.since_utc()
        )