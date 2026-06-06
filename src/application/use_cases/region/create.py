from dataclasses import dataclass

from src.application.dtos.region import RegionDTO
from src.application.ports.region.region_repo import RegionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.region import Region
from src.domain.value_objects.region_metadata import RegionMetadata
from src.infrastructure.database.transaction_manager.base import TransactionManager


@dataclass(frozen=True, eq=False)
class CreateRegionCommand(UseCaseRequest):
    title: str
    timezone: str
    channel_id: int
    channel_username: str
    metadata: RegionMetadata
    


@dataclass(kw_only=True)
class CreateRegionUseCase(UseCase[CreateRegionCommand, RegionDTO]):
    region_repo: RegionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: CreateRegionCommand) -> RegionDTO:
        region = await self.region_repo.create(
            Region.create(
                title=command.title,
                timezone=command.timezone,
                channel_id=command.channel_id,
                channel_username=command.channel_username,
                metadata=command.metadata,
            )
        )
        await self.transaction_manager.commit()
        return RegionDTO.from_entity(region)
