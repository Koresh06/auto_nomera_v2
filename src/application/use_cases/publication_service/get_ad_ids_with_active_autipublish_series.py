from dataclasses import dataclass

from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class GetAdIdsWithActiveAutopublishSeriesRequest(UseCaseRequest):
    ad_ids: list[int]


@dataclass(kw_only=True)
class GetAdIdsWithActiveAutopublishSeriesUseCase(
    UseCase[GetAdIdsWithActiveAutopublishSeriesRequest, set[int]]
):
    publication_repo: PublicationRepository

    async def __call__(
        self, command: GetAdIdsWithActiveAutopublishSeriesRequest
    ) -> set[int]:
        return await self.publication_repo.get_ad_ids_with_active_autopublish_series(
            ad_ids=command.ad_ids
        )
