from dataclasses import dataclass

from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.service_definition import ServiceDefinition


@dataclass(frozen=True, eq=False)
class GetByIdServiceDefinitionRequest(UseCaseRequest):
    id: int


@dataclass(kw_only=True)
class GetByIdServiceDefinitionUseCase(UseCase[GetByIdServiceDefinitionRequest, ServiceDefinitionDTO]):
    service_def_repo: ServiceDefinitionRepository

    async def __call__(self, command: GetByIdServiceDefinitionRequest) -> ServiceDefinitionDTO:
        service: ServiceDefinition = await self.service_def_repo.get_by_id(command.id)
        if service is None:
            raise ValueError("Услуга не найдена")
        return ServiceDefinitionDTO.from_entity(service)