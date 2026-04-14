from dataclasses import dataclass

from src.application.dtos.region import RegionDTO
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest


@dataclass(frozen=True, eq=False)
class IdRegionRequest(UseCaseRequest):
    region_id: int


@dataclass(kw_only=True)
class GegByIdRegionUseCase(UseCase[IdRegionRequest, RegionDTO]):
    region_repo: RegionRepository

    async def __call__(self, command: IdRegionRequest) -> RegionDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        return RegionDTO.from_entity(region)

