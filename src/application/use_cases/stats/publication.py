from dataclasses import dataclass

from src.application.dtos.publication_stats import PublicationStatsDTO
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.period import StatsPeriod


@dataclass(frozen=True, eq=False)
class GetPublicationStatsRequest(UseCaseRequest):
    period: StatsPeriod
    region_id: int | None = None


@dataclass(kw_only=True)
class GetPublicationStatsUseCase(
    UseCase[GetPublicationStatsRequest, PublicationStatsDTO]
):
    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetPublicationStatsRequest
    ) -> PublicationStatsDTO:
        return await self.publication_repo.get_stats(
            since_utc=command.period.since_utc(),
            region_id=command.region_id,
        )
