import logging
from dataclasses import dataclass

from src.domain.enums.region import RegionStatus
from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ToggleRegionStatusCommand(UseCaseRequest):
    region_id: int


@dataclass(kw_only=True)
class ToggleRegionStatusUseCase(UseCase[ToggleRegionStatusCommand, RegionDTO]):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: ToggleRegionStatusCommand) -> RegionDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)

        if region.status == RegionStatus.ACTIVE:
            region.disable()
        else:
            region.enable()

        region = await self.region_repo.update(region)
        await self.transaction_manager.commit()
        logger.info("Region status updated successfully for region %s", region.title)

        return RegionDTO.from_entity(region)
