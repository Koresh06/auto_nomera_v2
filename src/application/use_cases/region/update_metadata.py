import logging
from dataclasses import dataclass

from src.domain.value_objects.region_metadata import RegionMetadata
from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateRegionMetadataCommand(UseCaseRequest):
    region_id: int
    tg_group_url: str | None
    vk_group_url: str | None
    max_channel_url: str | None


@dataclass(kw_only=True)
class UpdateRegionMetadataUseCase(
    UseCase[UpdateRegionMetadataCommand, RegionDTO]
):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateRegionMetadataCommand) -> RegionDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)

        region.update_metadata(
            metadata=RegionMetadata(
                tg_group_url=command.tg_group_url,
                vk_group_url=command.vk_group_url,
                max_channel_url=command.max_channel_url,
            )
        )
        region = await self.region_repo.update(region)
        await self.transaction_manager.commit()
        logger.info("Region metadata updated successfully for region %s", region.title)
        
        return RegionDTO.from_entity(region)