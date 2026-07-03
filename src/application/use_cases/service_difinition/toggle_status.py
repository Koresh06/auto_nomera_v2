import logging
from dataclasses import dataclass

from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.exceptions.service_definition import ServiceDefinitionNotFoundException
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.infrastructure.database.transaction_manager.base import TransactionManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ToggleServiceStatusCommand(UseCaseRequest):
    service_id: int


@dataclass(kw_only=True)
class ToggleServiceStatusUseCase(UseCase[ToggleServiceStatusCommand, ServiceDefinitionDTO]):
    service_repo: ServiceDefinitionRepository
    transaction_manager: TransactionManager

    async def __call__(self, command: ToggleServiceStatusCommand) -> ServiceDefinitionDTO:
        service = await self.service_repo.get_by_id(command.service_id)
        if service is None:
            raise ServiceDefinitionNotFoundException(command.service_id)

        service.deactivate() if service.is_active else service.activate()
        service = await self.service_repo.save(service)
        await self.transaction_manager.commit()
        logger.info(f"[ToggleServiceStatus] service_id={service.id} status={service.is_active}")
        return ServiceDefinitionDTO.from_entity(service)