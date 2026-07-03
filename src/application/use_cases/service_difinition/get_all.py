from dataclasses import dataclass

from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.ports.publication_service.service_definition_repo import ServiceDefinitionRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.service_definition import ServiceDefinition


@dataclass(frozen=True, eq=False)
class GetAllServicesRequest(UseCaseRequest):
    is_active: bool | None = None


@dataclass(kw_only=True)
class GetAllServicesUseCase(UseCase[GetAllServicesRequest, list[ServiceDefinitionDTO]]):
    service_def_repo: ServiceDefinitionRepository

    async def __call__(self, command: GetAllServicesRequest) -> list[ServiceDefinitionDTO]:
        services: list[ServiceDefinition] = await self.service_def_repo.get_all(is_active=command.is_active)
        return [ServiceDefinitionDTO.from_entity(s) for s in services]