from dataclasses import dataclass

from src.application.dtos.ad import AdDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.ad import Ad
from src.domain.enums.ad import AdType


@dataclass(frozen=True, eq=False)
class CreateAdDraftRequest(UseCaseRequest):
    user_id: int
    region_id: int
    ad_type: AdType


@dataclass(kw_only=True)
class CreateAdDraftUseCase(UseCase[CreateAdDraftRequest, AdDTO]):
    ad_repo: AdRepository

    async def __call__(self, command: CreateAdDraftRequest) -> AdDTO:
        ad = Ad(
            user_id=command.user_id,
            region_id=command.region_id,
            ad_type=command.ad_type,
        )
        await self.ad_repo.create(ad)

        return AdDTO(
            id=ad.id,
            user_id=ad.user_id,
            region_id=ad.region_id,
            ad_type=ad.ad_type,
        )
