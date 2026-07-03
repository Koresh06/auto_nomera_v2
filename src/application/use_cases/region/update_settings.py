import logging
from dataclasses import dataclass, replace
from datetime import time
from decimal import Decimal

from src.application.common.unsent import UNSET, _Unset
from src.application.dtos.region import RegionDTO
from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class UpdateRegionSettingsCommand(UseCaseRequest):
    region_id: int
    slot_times: tuple[time, ...] | _Unset = UNSET
    days_range: int | _Unset = UNSET
    system_paid_slots_count: int | _Unset = UNSET
    publication_limit_enabled: bool | _Unset = UNSET
    paid_slot_price: Decimal | _Unset = UNSET


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

        changes = {}
        if not isinstance(command.slot_times, _Unset):
            changes["slot_times"] = command.slot_times
        if not isinstance(command.days_range, _Unset):
            changes["days_range"] = command.days_range
        if not isinstance(command.system_paid_slots_count, _Unset):
            changes["system_paid_slots_count"] = command.system_paid_slots_count
        if not isinstance(command.publication_limit_enabled, _Unset):
            changes["publication_limit_enabled"] = command.publication_limit_enabled
        if not isinstance(command.paid_slot_price, _Unset):
            changes["paid_slot_price"] = command.paid_slot_price

        new_settings = replace(region.settings, **changes)
        region.update_settings(settings=new_settings)

        region = await self.region_repo.update(region)
        await self.transaction_manager.commit()
        logger.info("Region settings updated successfully for region %s", region.title)

        return RegionDTO.from_entity(region)
