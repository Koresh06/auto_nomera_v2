from dataclasses import dataclass

from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.region import Region


@dataclass(frozen=True, eq=False)
class IdRegionRequest(UseCaseRequest):
    region_id: int


@dataclass(kw_only=True)
class GegByIdRegionUseCase(UseCase[IdRegionRequest, RegionDTO | None]):
    region_repo: RegionRepository

    async def __call__(self, command: IdRegionRequest) -> RegionDTO | None:
        region: Region | None = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)
        return RegionDTO.from_entity(region)
