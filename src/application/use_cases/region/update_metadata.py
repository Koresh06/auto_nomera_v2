import logging
from dataclasses import dataclass, replace

from src.application.common.unsent import UNSET, _Unset
from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateRegionMetadataCommand(UseCaseRequest):
    region_id: int
    tg_group_url: str | None | _Unset = UNSET
    vk_group_url: str | None | _Unset = UNSET
    max_channel_url: str | None | _Unset = UNSET


@dataclass(kw_only=True)
class UpdateRegionMetadataUseCase(UseCase[UpdateRegionMetadataCommand, RegionDTO]):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateRegionMetadataCommand) -> RegionDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)

        changes = {}
        if not isinstance(command.tg_group_url, _Unset):
            changes["tg_group_url"] = command.tg_group_url
        if not isinstance(command.vk_group_url, _Unset):
            changes["vk_group_url"] = command.vk_group_url
        if not isinstance(command.max_channel_url, _Unset):
            changes["max_channel_url"] = command.max_channel_url

        new_metadata = replace(region.metadata, **changes)
        region.update_metadata(metadata=new_metadata)

        region = await self.region_repo.update(region)
        await self.transaction_manager.commit()
        logger.info("Region metadata updated successfully for region %s", region.title)

        return RegionDTO.from_entity(region)
