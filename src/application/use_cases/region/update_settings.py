import logging
from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from src.domain.value_objects.region_settings import RegionSettings
from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateRegionSettingsCommand(UseCaseRequest):
    region_id: int
    slot_times: tuple[time, ...]
    days_range: int
    system_paid_slots_count: int
    publication_limit_enabled: bool
    paid_slot_price: Decimal


@dataclass(kw_only=True)
class UpdateRegionSettingsUseCase(
    UseCase[UpdateRegionSettingsCommand, RegionDTO]
):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: UpdateRegionSettingsCommand) -> RegionDTO:
        region = await self.region_repo.get_by_id(command.region_id)
        if region is None:
            raise RegionNotFoundException(command.region_id)

        region.update_settings(
            settings=RegionSettings(
                slot_times=command.slot_times,
                days_range=command.days_range,
                system_paid_slots_count=command.system_paid_slots_count,
                publication_limit_enabled=command.publication_limit_enabled,
                paid_slot_price=command.paid_slot_price,
            )
        )
        region = await self.region_repo.update(region)
        await self.transaction_manager.commit()
        logger.info("Region settings updated successfully for region %s", region.title)

        return RegionDTO.from_entity(region)
    
