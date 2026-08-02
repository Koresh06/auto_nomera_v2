from dataclasses import dataclass

from src.application.dtos.region import RegionDTO
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.services.region.sorting import sort_regions


@dataclass(frozen=True, eq=False)
class GetRegionsRequest(UseCaseRequest):
    pass


@dataclass(kw_only=True)
class GetAllRegionsUseCase(UseCase[GetRegionsRequest, list[RegionDTO]]):
    region_repo: RegionRepository

    async def __call__(self, command: GetRegionsRequest) -> list[RegionDTO]:
        regions = await self.region_repo.get_all()
        dtos = [RegionDTO.from_entity(r) for r in regions]
        return sort_regions(dtos)
