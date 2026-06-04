from dataclasses import dataclass

from src.application.dtos.region import RegionDTO
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class CreateRegionCommand(UseCaseRequest):
    title: str
    timezone: TimezoneName
    channel_id: int
    channel_username: str
    


@dataclass(kw_only=True)
class CreateRegionUseCase(UseCase[CreateRegionCommand, RegionDTO]):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreateRegionCommand) -> RegionDTO:
        region = await self.region_repo.create(
            Region(
                title=command.title,
                timezone=command.timezone,
                channel_id=command.channel_id,
                channel_username=command.channel_username,
            )
        )
        await self.transaction_manager.commit()
        return RegionDTO.from_entity(region)
