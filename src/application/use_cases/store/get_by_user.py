from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.dtos.ad import AdDTO


@dataclass(frozen=True, eq=False)
class GetUserStoreRequest(UseCaseRequest):
    user_id: int
    region_id: int


@dataclass(kw_only=True)
class GetUserStoreUseCase(UseCase[GetUserStoreRequest, AdDTO | None]):
    ad_repo: AdRepository

    async def __call__(self, command: GetUserStoreRequest) -> AdDTO | None:
        ad = await self.ad_repo.find_store_by_user(
            user_id=command.user_id,
            region_id=command.region_id,
        )
        if ad is None:
            raise AdNotFoundException
        return AdDTO.from_entity(ad)
