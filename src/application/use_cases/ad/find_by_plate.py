from dataclasses import dataclass

from src.application.dtos.ad import AdDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class FindAdByPlateRequest(UseCaseRequest):
    user_id: int
    region_id: int
    plate_number: str


@dataclass(kw_only=True)
class FindAdByPlateUseCase(UseCase[FindAdByPlateRequest, AdDTO | None]):
    ad_repo: AdRepository

    async def __call__(self, command: FindAdByPlateRequest) -> AdDTO | None:
        ad = await self.ad_repo.find_by_plate(
            user_id=command.user_id,
            region_id=command.region_id,
            plate_number=command.plate_number,
        )
        if ad is None:
            return None
        return AdDTO.from_entity(ad)
